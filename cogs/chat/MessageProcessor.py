import re
import logging
import discord
import time
from datetime import datetime
from google import genai
from google.genai import types

from cogs.chat.ChatHistoryHandler import ChatHistoryHandler
from cogs.chat.MediaProcessor import MediaProcessor
from cogs.chat.ResponseHandler import extract_response_text
from database.repo.ChannelConfigRepo import ChannelConfigRepo
from database.repo.MediaHandlerRepo import MediaHandlerRepo
from database.repo.PersonaRepo import PersonaRepo
from database.repo.WebhookInfoRepo import WebhookInfoRepo
from database.domain.MediaHandler import MediaHandler
from cogs.chat.ChatLock import ChatLock

from loader.Results import *


logger = logging.getLogger(__name__)


class MessageProcessor:
    """
    Single source of truth for processing messages — main bot AND webhooks.

    Flow: load history → cleanup expired media → process media →
          Gemini chat → save history → track media.

    When ``webhook_id`` is provided, uses the webhook's system instruction
    and a per-webhook chat history path.
    """

    def __init__(
        self,
        default_config: types.GenerateContentConfig,
        channel_config_repo: ChannelConfigRepo,
        media_hadnler_repo: MediaHandlerRepo,
        persona_repo: PersonaRepo,
        webhook_repo: WebhookInfoRepo,
        media_processor: MediaProcessor,
        chat_history_handler: ChatHistoryHandler,
        lock: ChatLock,
    ):
        self.default_config = default_config
        self.channel_config = channel_config_repo
        self.media_handler = media_hadnler_repo
        self.personaInfo = persona_repo
        self.webhookInfo = webhook_repo
        self.media_processor = media_processor
        self.chat_history_handler = chat_history_handler
        self.lock = lock
        self.safetly_setting = [
            types.SafetySetting(category='HARM_CATEGORY_HATE_SPEECH', threshold="OFF"),
            types.SafetySetting(category='HARM_CATEGORY_HARASSMENT', threshold="OFF"),
            types.SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold="OFF"),
            types.SafetySetting(category='HARM_CATEGORY_DANGEROUS_CONTENT', threshold="OFF")
        ]
        self.default_tools = [
            types.Tool(url_context=types.UrlContext()),
            types.Tool(code_execution=types.ToolCodeExecution),
            types.Tool(googleSearch=types.GoogleSearch()),
        ]

    def _get_ids(self, message: discord.Message) -> tuple[str, str]:
        """Extracts server_id and channel_id from a discord message."""
        if isinstance(message.channel, discord.DMChannel):
            server_id = "direct_messages"
        else:
            server_id = str(message.guild.id)
        channel_id = str(message.channel.id)
        return server_id, channel_id

    def _has_media(self, message: discord.Message) -> bool:
        """Checks if the message has attachments or media URLs."""
        if message.attachments:
            return True
        urls = re.findall(r"(https?://[^\s]+)", message.content)
        return len(urls) > 0

    def _build_webhook_config(self, system_instruction: str) -> types.GenerateContentConfig:
        """
        Builds a Gemini config for a webhook using its system instruction.
        Copies settings from default_config but uses the webhook's instruction.
        """
        default_safety = [
            types.SafetySetting(category='HARM_CATEGORY_HATE_SPEECH', threshold="OFF"),
            types.SafetySetting(category='HARM_CATEGORY_HARASSMENT', threshold="OFF"),
            types.SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold="OFF"),
            types.SafetySetting(category='HARM_CATEGORY_DANGEROUS_CONTENT', threshold="OFF")
        ]

        default_tools = [
            types.Tool(url_context=types.UrlContext()),
            types.Tool(code_execution=types.ToolCodeExecution),
            types.Tool(googleSearch=types.GoogleSearch()),
        ]

        config = self.default_config

        return types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=(config.temperature or 1.0) if config else 1.0,
            top_p=(config.top_p or 0.95) if config else 0.95,
            top_k=(config.top_k or 20) if config else 20,
            candidate_count=(config.candidate_count or 1) if config else 1,
            max_output_tokens=(config.max_output_tokens or 65536) if config else 65536,
            safety_settings=(config.safety_settings or default_safety) if config else default_safety,
            tools=(config.tools or default_tools) if config else default_tools,
        )

    # too many task for a single function
    async def process(
        self,
        message: discord.Message,
        bot_user: discord.User,
        webhook_id: str | None = None,
    ) -> tuple[str, any]:
        """
        Main entry point. Processes the message and returns (text_response, image_data).

        Args:
            message: The Discord message to process.
            webhook_id: If set, process as a webhook character using it
                        system instruction and per-webhook history.
                        If None, process as the main bot.
        """
        server_id, channel_id = self._get_ids(message)

        # Resolve which API key and model to use
        channelConfig = await self.channel_config.get(channel_id=channel_id)

        match channelConfig:
            case Error():
                return channelConfig.message, None
                
            
        if not channelConfig.data.api_key:
            return "Api is empty", None

        api_key = channelConfig.data.api_key
        model_name = channelConfig.data.model_name or "gemini-flash-latest"

        
        client = genai.Client(api_key=api_key)

        # Determine history path and config based on main bot vs webhook
        if webhook_id:
            # Per-webhook history: data/chat/{channel}/{chat_id}_chat_history.pkl
            chat_id = f"{webhook_id}_{channel_id}"
            #try to add lock
            
            system_instruction = await self.webhookInfo.get_bot_info(bot_id=int(webhook_id))
            if not system_instruction:
                logger.warning("No system instruction found for webhook %s", webhook_id)
                system_instruction = "You are a helpful assistant."
            config = types.GenerateContentConfig(
                system_instruction=system_instruction.data,
                temperature=1.0,
                top_p=0.95,
                top_k=20,
                candidate_count=1,
                max_output_tokens=65536,
                safety_settings=self.safetly_setting,
                tools=self.default_tools
            )
        else:
            chat_id = f"main_bot_{channel_id}"
            config = self.default_config

        result = self.lock.add_chat_to_lock(chat_id)
        if not result:
            return f"<@{message.author.id}> ⚠️ {message.id} is still processing. Please wait.", None

        await message.add_reaction('\U0001F534')

        #load the index that have the more then set timelimit
        before_time_limit = 44*60*60

        expiredIndex = await self.media_handler.get_expired_by_channel(
            channel_id=channel_id,
            before_timestamp=time.time() - before_time_limit
        )

        match expiredIndex:
            case Error():
                #remove the lock
                self.lock.unlock_chat(chat_id)
                await message.remove_reaction('\U0001F534',bot_user)
                return f"Can't check the chat for media files.\n{expiredIndex.message}", None
            
        history_index: list[int] = []

        for item in expiredIndex.data:
            history_index.append(item.index_in_history)

        #load the chat history
        chat_history = await self.chat_history_handler.load(channel_id=channel_id,chat_id=chat_id)
        #if history index is more then 1, then remove the history
        if len(history_index) > 0:
            chat_history = await self.chat_history_handler.remove_items(chat=chat_history,indices=history_index)
            match chat_history:
                case Error():
                    self.lock.unlock_chat(chat_id)
                    await message.remove_reaction('\U0001F534',bot_user)
                    return f"Error while removing the history.\n{chat_history.message}",None
                case Success(): chat_history = chat_history.data

        #chat history is loaded        

        # Format user message with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_message = f"{timestamp} - ({message.author.name},[{message.author.id}]): {message.content}"

        # Track current message index for media 
        # the size gives the total lenght which is max index + 1
        # we can assume new message would increase the index by one
        message_index = len(chat_history)

        # Process media if present
        media_parts = []
        file_uris = []

        if self._has_media(message):
            logger.info("Processing media for message %d in %s/%s", message.id)
            media_parts, file_uris = await self.media_processor.process(message, client)
            logger.info("Got %d media parts, %d file URIs", len(media_parts), len(file_uris))

        # ── Gemini interaction ──
        try:
            #conversation_history = getattr(chat_history, '_curated_history', None)
            # Create Gemini chat session with history
            chat = client.aio.chats.create(
                model=model_name,
                config=config,
                history=chat_history,
            )

            # Build the message content
            if media_parts:
                content = [user_message, *media_parts]
            else:
                content = user_message

            # Send message to Gemini
            response = await chat.send_message(content)

        except Exception as e:
            history_len = (len(chat_history) if chat_history else 0)

            # 1. Try to grab the clean message directly from the exception object
            clean_error_msg = getattr(e, 'message', None)

            # 2. If it's buried in a string dictionary, use Regex to fish it out safely
            if not clean_error_msg:
                raw_error = str(e)
                # This looks for 'message': 'ANYTHING HERE' and grabs the text inside
                match = re.search(r"['\"]message['\"]:\s*['\"](.*?)['\"]", raw_error)
                clean_error_msg = match.group(1) if match else raw_error

            # Keep your logger logging the FULL error for your console
            logger.error(
                "Gemini interaction failed for message %d: %s\n"
                "History entries: %d, webhook_id: %s",
                message.id, e, history_len, webhook_id,
            )
            
            self.lock.unlock_chat(chat_id)
            await message.remove_reaction('\U0001F534', bot_user)
            
            # Return ONLY the clean message to Discord
            return f"⚠️ Failed to get a response from the model:\n```{clean_error_msg}```", None
        

        # checking the response
        if response is None:
            logger.warning("Gemini returned None response for message %d", message.id)
            self.lock.unlock_chat(chat_id)
            await message.remove_reaction('\U0001F534',bot_user)
            return "⚠️ No response from the model (response was empty).", None

        if not response.candidates:
            logger.warning(
                "Gemini response has no candidates for message %d.\n"
                "Raw response: %s",
                message.id, response,
            )
            self.lock.unlock_chat(chat_id)
            await message.remove_reaction('\U0001F534',bot_user)
            return "⚠️ Response was blocked by safety filters (no candidates).", None

        first_candidate = response.candidates[0]
        if not first_candidate.content or not first_candidate.content.parts:
            logger.warning(
                "Gemini response content is null for message %d.\n"
                "Candidate finish_reason: %s\n"
                "Raw candidate: %s",
                message.id,
                getattr(first_candidate, 'finish_reason', 'unknown'),
                first_candidate,
            )
            self.lock.unlock_chat(chat_id)
            await message.remove_reaction('\U0001F534',bot_user)
            return "⚠️ Response was blocked by safety filters (content was null).", None

        # Extract text and images from response
        text_response, image_data = await extract_response_text(response)

        # Save history
        save_status = await self.chat_history_handler.save(channel_id=channel_id, chat_id=chat_id,chat_history=chat.get_history())
        match save_status:
            case Error():
                self.lock.unlock_chat(chat_id)
                return f"Error happened while saving the response.",None
        # Track uploaded media files for expiry
        if file_uris:
            save_status = await self.media_handler.save(
                MediaHandler(
                    chat_id=chat_id,
                    channel_id=channel_id,
                    timestamp=time.time(),
                    index_in_history=message_index
                )
            )

            match save_status:
                case Error():
                    self.lock.unlock_chat(chat_id)
                    await message.remove_reaction('\U0001F534',bot_user)
                    return f"Can't save the data in the media handler table\n {save_status.message}", None
                
        self.lock.unlock_chat(chat_id)
        await message.remove_reaction('\U0001F534',bot_user)

        return text_response, image_data
