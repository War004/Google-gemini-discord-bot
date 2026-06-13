import discord

from discord.ext import commands
from charset_normalizer import from_bytes
from discord import app_commands
from database.repo.WebhookInfoRepo import WebhookInfoRepo
from database.repo.MediaHandlerRepo import MediaHandlerRepo
from src.translator.translator import Translator
from src.BloomFilter import BloomFilter
from src.PersonCache import PersonCache

from src.loader.Results import *
from src.utils.PngParserResults import PngParserResults

from discord.webhook import Webhook

from database.domain.WebhookInfo import WebhookInfo
from typing import Optional
from PIL import Image
import io
import base64
import json
import re
import asyncio
import discord
from google import genai
from google.genai import types
from google.genai.types import SafetySetting, Tool, ThinkingConfig, Content, Part
from src.cogs.chat.ChatHistoryHandler import ChatHistoryHandler
from src.cogs.chat.ResponseHandler import send_response
from src.PersonCache import PersonCache
from database.repo.ChannelConfigRepo import ChannelConfigRepo as ChannelRepo
import magic
import json
import re

from src.translator.lan_key import LangKey

class WebhookCom(commands.Cog):
    def __init__(
            self, 
            bot: commands.Bot,
            api_bloom: BloomFilter,
            lan_bloom: BloomFilter,
            channel_config: ChannelRepo,
            webhook_repo: WebhookInfoRepo,
            person_cache: PersonCache,
            chat_history_handler: ChatHistoryHandler,
            string_translator: Translator,
            media_repo: MediaHandlerRepo
            ):
        self.bot = bot
        self.api_bloom = api_bloom
        self.lan_bloom = lan_bloom
        self.webhook_repo = webhook_repo
        self.channel_repo = channel_config
        self.person_cache = person_cache
        self.chat_history_handler = chat_history_handler
        self.string_translator = string_translator
        self.media_repo = media_repo
        self.persona_describe_guideness = """
            Do as the user saying to do
            """
    #Add commands only releated to the webhooks
    """
    1. add webhook
    Params: name, !avatar, !text_ins, !plain_text_ins
    2. remove webhook
    Params:
    3. remove all webhook
    Params: 
    4. clear webhook message
    Params:
    5. add v2_character card
    Params: image data, persona image
    6. remove all exepect
    Params: 
    """
    
    #directly using discord attachment instead of image bytes
    # because want to actually handle parsing, but makes the function tied to discord attachment, but it is a discord bot.
    async def parse_png_image(self,image: discord.Attachment,lan_code:str) -> Success[PngParserResults] | Error:
        MAX_SIZE_IMAGE = 25_000_000 # 50 MB limit
        MB_DIVISOR = 1_000_000
        PNG_MAGIC = b'\x89PNG\r\n\x1a\n'

        if image.size > MAX_SIZE_IMAGE:
            message = self.string_translator.get_translation_via_bypass_db(
                string_key = LangKey.IMAGE_MAX_SIZE_EXCEED,
                lan_code = lan_code,
                payload={
                    "max_allowed_mb":MAX_SIZE_IMAGE/MB_DIVISOR,
                    "current_image_size":image.size/MB_DIVISOR
                }
            )
            """
            solution = self.string_translator.get_translation_via_bypass_db(
                string_key = None,
                lan_code = lan_code,
                direct_message = "Upload a smaller message."
            )"""
                    
            return Error(
                message=message,
            )
        
        if not image.content_type == "image/png":
            message = self.string_translator.get_translation_via_bypass_db(
                string_key = LangKey.IMAGE_NOT_PNG,
                lan_code = lan_code,
                payload={
                    "file_type":image.content_type
                }
            )
            """
            solution = self.string_translator.get_translation_via_bypass_db(
                string_key = None,
                lan_code = lan_code,
                direct_message = "Upload a png file with is encoding with v2 card specs"
            )"""

            return Error(
                message = message,
            )
        
        image_bytes = await image.read()

        img = Image.open(io.BytesIO(image_bytes))
        meta_data = img.text
        base64_message = meta_data.get('chara','')

        if not base64_message:
            message = self.string_translator.get_translation_via_bypass_db(
                string_key=LangKey.CHAR_DEF_NOT_FOUND,
                lan_code=lan_code
            )
            return Error(
                message=message
            )
        
        decoded_bytes = base64.b64decode(base64_message)

        results = from_bytes(decoded_bytes).best()

        if results is None:
            message = self.string_translator.get_translation_via_bypass_db(
                string_key=LangKey.CHAR_DEF_DECODE_FAILED,
                lan_code=lan_code,
            )
            return Error(
                message=message
            )
        
        extracted_text = str(results)

        try:
            character_data = json.loads(extracted_text)
        except json.JSONDecodeError:
            message = self.string_translator.get_translation_via_bypass_db(
                string_key=LangKey.CHAR_DEF_DECODE_FAILED,
                lan_code=lan_code,
            )
            return Error(
                message=message
            )
        
        character_data = character_data.get('data', character_data)

        name = character_data.get('name','untitled')[:80]

        if 'discord' in name.lower():
            name = re.sub('discord','******', name, flags=re.IGNORECASE)
        
        description = character_data.get('description', 'There was no description, continuing without it')
        scenario = character_data.get('scenario', 'There was no scenario, continuing without it')
        system_prompt = character_data.get('system_prompt', 'There was no system_prompt, follow the instructions given at the start of the conversation')
        message_example = character_data.get('mes_example','No, message example was provided, continuing without it, follow the format for the first actual message from the roleplay')
        first_message = character_data.get('first_mes','No first message found. Just reply to this message to start the conversation')

        return Success(
            data=PngParserResults(
                name=name,
                profileImage= image_bytes,
                description=description,
                scenario=scenario,
                system_prompt=system_prompt,
                message_example=message_example,
                first_message=first_message
            )
        )
    
    async def create_webhook_dropdown(self, interaction: discord.Interaction, placeholder: str,lan_code: str, callback):

        
        if isinstance(interaction.channel, discord.DMChannel):
            message = self.string_translator.get_translation_via_bypass_db(
                string_key=LangKey.WEBHOOK_NO_DM,
                lan_code=lan_code
            )

            await interaction.followup.send(message, ephemeral=True)
            return

        try:
            #get all webhook
            webhooks = await interaction.channel.webhooks()
            bot_webhook = []

            if len(webhooks) < 1 or webhooks is None:
                message = self.string_translator.get_translation_via_bypass_db(
                    string_key=LangKey.NO_WEBHOOK_FOUND,
                    lan_code=lan_code
                )
                
                await interaction.followup.send(message)
                return
            #start the loop to delete
            webhooks:list[Webhook] = await interaction.channel.webhooks()

            for webhook in webhooks:
                if(webhook.user == self.bot.user):
                    bot_webhook.append(webhook)

            #add the options 10 webhooks are the limit far more then 25 item in discord list
            options = [
                *[discord.SelectOption(label=webhook.name,value=str(webhook.id)) for webhook in bot_webhook]
            ]

            view = discord.ui.View()
            dropdown = discord.ui.Select(
                placeholder=placeholder,
                options=options
            )
            dropdown.callback = callback
            view.add_item(dropdown)

            return view
        except Exception as e:
            # [AutoFix] Replaced match type(e) with isinstance — match type(e) used structural
            # pattern matching, causing the first case to always match as a capture pattern.
            if isinstance(e, discord.Forbidden):
                message = self.string_translator.get_translation_via_bypass_db(
                    string_key=LangKey.WEBHOOK_NO_MANAGE_PERM_CHANNEL,
                    lan_code=lan_code,
                    payload={
                        "channel_name": interaction.channel.name
                    }
                )
                await interaction.followup.send(message)
            elif isinstance(e, discord.HTTPException):
                message = self.string_translator.get_translation_via_bypass_db(
                    string_key=LangKey.FETCH_WEBHOOK_HTTP_ERROR,
                    lan_code=lan_code
                )
                await interaction.followup.send(message)
            else:
                message = self.string_translator.get_translation_via_bypass_db(
                    string_key=LangKey.WEBHOOK_LIST_UNKNOWN_ERROR,
                    lan_code=lan_code
                )
                await interaction.followup.send(message)
            print(f"[WebhookCom] create_webhook_dropdown Exception: {type(e).__name__}: {e}")
            return None
        
    webhook_group = app_commands.Group(name="webhook", description="Manage all webhook settings")

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        #This was added as hosting happens in India, latency is high between US and India
        await interaction.response.defer()
        requires_api = {"add-v2-character-card"}

        api_hit = self.api_bloom.check(interaction.channel_id)
        lan_hit = self.lan_bloom.check(interaction.channel_id)
        local_lan_code = str(interaction.locale).split("-")[0]

        if lan_hit:
            db_result = await self.channel_repo.get_lan_code(interaction.channel_id)
            match db_result:
                case Success():
                    local_lan_code = db_result.data
                case Error():
                    message = self.string_translator.get_translation_via_bypass_db(
                        string_key=LangKey.LAN_DATA_NOT_SUCCESSFUL,
                        lan_code=local_lan_code
                    )
                    await interaction.followup.send(message)

        if interaction.command.name in requires_api:
            if api_hit == False:
                message = self.string_translator.get_translation_via_bypass_db(
                    string_key=LangKey.API_REQUIRED,
                    lan_code=local_lan_code
                )
                await interaction.followup.send(message)
                return False
        interaction.extras["lan_code"] = local_lan_code
        return True      

    @webhook_group.command(
        name=app_commands.locale_str("add"), 
        description=app_commands.locale_str("Manually add a webhook(with selection of avatar image and system instructions.)")
    )
    @app_commands.describe(
        name=app_commands.locale_str("Webhook's Name"),
        avatar=app_commands.locale_str("[Optional] The profile image for the webhook (png/jpg/webp)"),
        plain_text_instructions=app_commands.locale_str("[This or text file]System instructions as plain text."),
        text_file_instructions=app_commands.locale_str("[This or plan]System instructions as a text file attachment.")
    )
    async def add_raw_webhook(
        self,
        interaction: discord.Interaction,
        name: str,
        avatar: discord.Attachment = None,
        plain_text_instructions: str = None,
        text_file_instructions: discord.Attachment = None
    ):
        lan_code = interaction.extras.get(LangKey.LAN_CODE)
        MAX_SIZE_TEXT = 100_000 # 100 KB limit
        MAX_SIZE_IMAGE = 25_000_000 # 25 MB limit
        MB_DIVISOR = 1_000_000

        if isinstance(interaction.channel, discord.DMChannel):
            message = self.string_translator.get_translation_via_bypass_db(
                    string_key=LangKey.WEBHOOK_NO_DM,
                    lan_code=lan_code
                )
            await interaction.followup.send(message, ephemeral=True)
            return

        try:
            if (plain_text_instructions is None) == (text_file_instructions is None):
                    message = self.string_translator.get_translation_via_bypass_db(
                        string_key=LangKey.WEBHOOK_EMPTY_SYSTEM_INSTRUCTIONS,
                        lan_code=lan_code
                    )
                    await interaction.followup.send(message)
                    return
            if plain_text_instructions:
                 system_instructions = plain_text_instructions
            else:
                if not text_file_instructions.content_type.startswith("text/"):
                    message = self.string_translator.get_translation_via_bypass_db(
                        string_key=LangKey.TEXT_FILE_NOT_TEXT,
                        lan_code=lan_code
                    )
                    await interaction.followup.send(message)
                    return
                if text_file_instructions.size > MAX_SIZE_TEXT:
                    message = self.string_translator.get_translation_via_bypass_db(
                        string_key=LangKey.TEXT_FILE_SIZE_EXCEEDED,
                        lan_code=lan_code,
                        payload={
                            "max_size": str(MAX_SIZE_TEXT),
                            "current_size": str(text_file_instructions.size)
                        }
                    )
                    await interaction.followup.send(message)
                    return
                
                sys_bytes = await text_file_instructions.read()
                system_instructions = from_bytes(sys_bytes).best()
            
            #avtar processing
            avatar_bytes = None

            if avatar:
                if avatar.content_type not in ["image/png", "image/jpeg", "image/webp"]:
                    message = self.string_translator.get_translation_via_bypass_db(
                        string_key=LangKey.IMAGE_INVALID_FORMAT,
                        lan_code=lan_code
                    )
                    await interaction.followup.send(message)
                    return
                
                if avatar.size > MAX_SIZE_IMAGE:
                    message = self.string_translator.get_translation_via_bypass_db(
                        string_key=LangKey.IMAGE_SIZE_EXCEEDED,
                        lan_code=lan_code,
                        payload={
                            "max_size_mb": str(MAX_SIZE_IMAGE/MB_DIVISOR),
                            "current_size": str(avatar.size)
                        }
                    )
                    await interaction.followup.send(message)
                    return
                
                avatar_bytes = await avatar.read()
            
            #create the webhook now!

            webhook: Webhook | None = None

            try:
                webhook = await interaction.channel.create_webhook(name=name, avatar=avatar_bytes)
            except Exception as e:
                print(f"An error occurred while adding webhook: {e}")

            # exepection related would be catced on the expection block
            # webhook is going to be non null

            #add the webhook entry to the webhook repo
            #need to handle as it return a custom results,
            # NOTE: lan_code is not passed to DB repository methods because cogs use Success/Error wrapper checks for user-facing translations.
            result = await self.webhook_repo.save(
                WebhookInfo(
                    webhook_id=str(webhook.id),
                    channel_id=str(interaction.channel_id),
                    webhook_system_information = system_instructions
                )
            )
            match result:
                case Error():
                    message = self.string_translator.get_translation_via_bypass_db(
                        string_key=LangKey.WEBHOOK_DB_SAVE_FAILED,
                        lan_code=lan_code
                    )

                    await webhook.delete()
                    
                    await interaction.followup.send(message)
                
                case Success():
                    print(f"Saved the webhook for {interaction.guild.name}")
                    print(f"Webhook name: {webhook.name}")

                    message = self.string_translator.get_translation_via_bypass_db(
                        string_key=LangKey.WEBHOOK_READY,
                        lan_code=lan_code,
                        payload={
                            "webhook_id": str(webhook.id)
                        }
                    )
                    webhook_message = self.string_translator.get_translation_via_bypass_db(
                        string_key=LangKey.WEBHOOK_START_CONVERSATION,
                        lan_code=lan_code
                    )

                    await interaction.followup.send(message)
                    await webhook.send(webhook_message)

        except Exception as e:
            # [AutoFix] Replaced match type(e) with isinstance — Forbidden checked before
            # HTTPException since Forbidden is a subclass of HTTPException.
            if isinstance(e, discord.Forbidden):
                #No permission
                message = self.string_translator.get_translation_via_bypass_db(
                            string_key=LangKey.WEBHOOK_NO_CREATE_PERM,
                            lan_code=lan_code,
                            payload={
                                "channel_id": str(interaction.channel_id)
                            }
                        )
                await interaction.followup.send(message)
            elif isinstance(e, discord.HTTPException):
                message = self.string_translator.get_translation_via_bypass_db(
                            string_key=LangKey.DISCORD_INTERACTION_ERROR,
                            lan_code=lan_code
                        )
                # Discord API failure (rate limit, outage, invalid avatar, etc.)
                await interaction.followup.send(message)
            else:
                message = self.string_translator.get_translation_via_bypass_db(
                    string_key=LangKey.UNEXPECTED_ERROR,
                    lan_code=lan_code
                )
                await interaction.followup.send(message)
            print(f"[WebhookCom] Exception: {type(e).__name__}: {e}")

    @webhook_group.command(
        name=app_commands.locale_str("remove"),
        description=app_commands.locale_str("Removes the selected webhook")
    )
    async def remove_webhook_function(self,interaction: discord.Interaction):

        lan_code = interaction.extras.get(LangKey.LAN_CODE)

        if isinstance(interaction.channel, discord.DMChannel):
            message = self.string_translator.get_translation_via_bypass_db(
                    string_key=LangKey.WEBHOOK_NO_DM,
                    lan_code=lan_code
                )
            await interaction.followup.send(message, ephemeral=True)
            return

        async def remove_webhook_callback(interaction: discord.Interaction):
            await interaction.response.defer()
            selected_value = interaction.data['values'][0]

            try:
                # Fetch the webhook to ensure it still exists before deleting
                webhook_to_delete = await self.bot.fetch_webhook(int(selected_value))

                webhook_id = selected_value
                chat_id=f"{webhook_id}_{interaction.channel_id}"

                if webhook_to_delete:
                    await webhook_to_delete.delete()

                webhook_result, media_result, history_result = await asyncio.gather(
                    self.webhook_repo.delete(webhook_to_delete.id),
                    self.media_repo.delete(chat_id),
                    asyncio.to_thread(self.chat_history_handler.delete_history, str(interaction.channel_id), chat_id)
                )

                if isinstance(media_result, Error):
                    print(f"Error deleting media info: {media_result.message}")
                elif isinstance(media_result, Success):
                    print(f"Successfully deleted media info from database: {media_result.data}")

                if history_result is False:
                    print(f"Error deleting chat history for {chat_id}")
                else:
                    print(f"Successfully deleted chat history for {chat_id}")

                match webhook_result:
                    case Error():
                        print("Data unconsity, the webhook deleted from the server but remain present in the db")
                        print(f"Bot id: {webhook_to_delete.id}")
                        print("--ERROR LINE--")
                        print(webhook_result.message)
                        print(webhook_result.exception)

                        message = self.string_translator.get_translation_via_bypass_db(
                            string_key=LangKey.WEBHOOK_DELETE_DB_INCONSISTENCY,
                            lan_code=lan_code,
                            payload={
                                "webhook_name": webhook_to_delete.name
                            }
                        )
                        await interaction.followup.send(message)
                        return
                    case Success():
                        print(f"Successfully deleted webhook info from database: {webhook_result.data}")
                
                message = self.string_translator.get_translation_via_bypass_db(
                    string_key=LangKey.WEBHOOK_REMOVED,
                    lan_code=lan_code,
                    payload={
                        "webhook_name": webhook_to_delete.name
                    }
                )
                await interaction.followup.send(message)
            
            
            except Exception as e:
                # [AutoFix] Replaced match type(e) with isinstance — NotFound checked before
                # HTTPException since NotFound is a subclass of HTTPException.
                if isinstance(e, discord.NotFound):
                    message = self.string_translator.get_translation_via_bypass_db(
                        string_key=LangKey.WEBHOOK_NOT_EXIST_ALREADY_DELETED,
                        lan_code=lan_code
                    )
                    await interaction.followup.send(message)
                elif isinstance(e, discord.HTTPException):
                    message = self.string_translator.get_translation_via_bypass_db(
                        string_key=LangKey.HTTP_ERROR,
                        lan_code=lan_code
                    )
                    await interaction.followup.send(message)
                else:
                    message = self.string_translator.get_translation_via_bypass_db(
                        string_key=LangKey.UNEXPECTED_ERROR,
                        lan_code=lan_code
                    )
                    await interaction.followup.send(message)
                print(f"[WebhookCom] Exception: {type(e).__name__}: {e}")
        #create a view here, todo create_webhook_dropdown

        dropdown_placeholder_msg = self.string_translator.get_translation_via_bypass_db(
            string_key=LangKey.SELECT_TO_REMOVE,
            lan_code=lan_code
        )

        select_to_remove_msg = self.string_translator.get_translation_via_bypass_db(
            string_key=LangKey.SELECT_TO_REMOVE,
            lan_code=lan_code
        )
        
        view = await self.create_webhook_dropdown(interaction, dropdown_placeholder_msg, lan_code, remove_webhook_callback)
        if view:
            await interaction.followup.send(select_to_remove_msg, view=view)

    #remove all webhook no need of a view
    @webhook_group.command(
        name=app_commands.locale_str("remove-all"),
        description=app_commands.locale_str("Removes all the webhook in the channel.")
    )
    async def remove_all_webhook_function(self,interaction: discord.Interaction):
        lan_code = interaction.extras.get(LangKey.LAN_CODE)

        if isinstance(interaction.channel, discord.DMChannel):
            message = self.string_translator.get_translation_via_bypass_db(
                string_key=LangKey.WEBHOOK_NO_DMS,
                lan_code=lan_code
            )
            await interaction.followup.send(message, ephemeral=True)
            return

        try:
            #get all webhook
            webhooks = await interaction.channel.webhooks()

            if len(webhooks) < 1: 
                message = self.string_translator.get_translation_via_bypass_db(
                    string_key=LangKey.NO_WEBHOOK_FOUND_IN_CHANNEL,
                    lan_code=lan_code
                )
                await interaction.followup.send(message)
                return
            #start the loop to delete
            total_deleted = 0
            error_deleted = 0
            for webhook in webhooks:
                if webhook.user == self.bot.user:
                    #delete the webhook, also in future delete the chat folder and etrc..
                    await webhook.delete()
                    chat_id = f"{webhook.id}_{interaction.channel_id}"

                    webhook_result, media_result, history_result = await asyncio.gather(
                        self.webhook_repo.delete(webhook.id),
                        self.media_repo.delete(chat_id),
                        asyncio.to_thread(self.chat_history_handler.delete_history, str(interaction.channel_id), chat_id)
                    )

                    if isinstance(media_result, Error):
                        print(f"Error deleting media info: {media_result.message}")
                    elif isinstance(media_result, Success):
                        print(f"Successfully deleted media info from database: {media_result.data}")

                    if history_result is False:
                        print(f"Error deleting chat history for {chat_id}")
                    else:
                        print(f"Successfully deleted chat history for {chat_id}")

                    match webhook_result:
                        case Error():
                            msg = self.string_translator.get_translation_via_bypass_db(
                                string_key=LangKey.WEBHOOK_DELETE_DB_FAILED,
                                lan_code=lan_code,
                                payload={
                                    "webhook_name": webhook.name
                                }
                            )
                            await interaction.followup.send(msg)
                            print(webhook_result.message)
                            print(webhook_result.exception)
                            error_deleted +=1
                        case Success():
                            print(f"Successfully deleted webhook info from database: {webhook_result.data}")
                            total_deleted +=1
            
            final_msg = self.string_translator.get_translation_via_bypass_db(
                string_key=LangKey.WEBHOOKS_DELETED,
                lan_code=lan_code,
                payload={
                    "total_deleted": str(total_deleted)
                }
            )
            await interaction.followup.send(final_msg)
        except Exception as e:
            # [AutoFix] Replaced match type(e) with isinstance — Forbidden checked before
            # HTTPException since Forbidden is a subclass of HTTPException.
            if isinstance(e, discord.Forbidden):
                msg = self.string_translator.get_translation_via_bypass_db(
                    string_key=LangKey.WEBHOOK_NO_MANAGE_PERM_CHANNEL,
                    lan_code=lan_code,
                    payload={
                        "channel_name": interaction.channel.name
                    }
                )
                await interaction.followup.send(msg)
            elif isinstance(e, discord.HTTPException):
                msg = self.string_translator.get_translation_via_bypass_db(
                    string_key=LangKey.HTTP_ERROR_MSG,
                    lan_code=lan_code
                )
                await interaction.followup.send(msg)
            else:
                msg = self.string_translator.get_translation_via_bypass_db(
                    string_key=LangKey.UNEXPECTED_ERROR,
                    lan_code=lan_code
                )
                await interaction.followup.send(msg)
            print(f"[WebhookCom] Exception: {type(e).__name__}: {e}")
    
    @webhook_group.command(
        name=app_commands.locale_str("remove-all-except"),
        description=app_commands.locale_str("Removes all the webhook in the channel except the selected one.")
    )
    async def remove_all_webhook_except_function(self,interaction: discord.Interaction):
        lan_code = interaction.extras.get(LangKey.LAN_CODE)

        if isinstance(interaction.channel, discord.DMChannel):
            message = self.string_translator.get_translation_via_bypass_db(
                string_key=LangKey.WEBHOOK_NO_DMS,
                lan_code=lan_code
            )
            await interaction.followup.send(message, ephemeral=True)
            return
        
        async def remove_all_except_callback(interaction: discord.Interaction):
            await interaction.response.defer()
            selected_value = interaction.data['values'][0]

            try:
                webhook_to_save = await self.bot.fetch_webhook(int(selected_value))
                
                #get all webhook
                webhooks = await interaction.channel.webhooks()

                if len(webhooks) < 1: 
                    message = self.string_translator.get_translation_via_bypass_db(
                        string_key=LangKey.NO_WEBHOOK_FOUND_IN_CHANNEL,
                        lan_code=lan_code
                    )
                    await interaction.followup.send(message)
                    return
                #start the loop to delete
                total_deleted = 0
                error_deleted = 0
                for webhook in webhooks:
                    if webhook.user == self.bot.user and webhook != webhook_to_save:
                        #delete the webhook, also in future delete the chat folder and etrc..
                        await webhook.delete()
                        chat_id = f"{webhook.id}_{interaction.channel_id}"

                        webhook_result, media_result, history_result = await asyncio.gather(
                            self.webhook_repo.delete(webhook.id),
                            self.media_repo.delete(chat_id),
                            asyncio.to_thread(self.chat_history_handler.delete_history, str(interaction.channel_id), chat_id)
                        )

                        if isinstance(media_result, Error):
                            print(f"Error deleting media info: {media_result.message}")
                        elif isinstance(media_result, Success):
                            print(f"Successfully deleted media info from database: {media_result.data}")

                        if history_result is False:
                            print(f"Error deleting chat history for {chat_id}")
                        else:
                            print(f"Successfully deleted chat history for {chat_id}")

                        match webhook_result:
                            case Error():
                                msg = self.string_translator.get_translation_via_bypass_db(
                                    string_key=LangKey.WEBHOOK_DELETE_DB_FAILED,
                                    lan_code=lan_code,
                                    payload={
                                        "webhook_name": webhook.name
                                    }
                                )
                                await interaction.followup.send(msg)
                                print(webhook_result.message)
                                print(webhook_result.exception)
                                error_deleted += 1
                            case Success():
                                print(f"Successfully deleted webhook info from database: {webhook_result.data}")
                                total_deleted += 1
                
                final_msg = self.string_translator.get_translation_via_bypass_db(
                    string_key=LangKey.WEBHOOKS_DELETED,
                    lan_code=lan_code,
                    payload={
                        "total_deleted": str(total_deleted)
                    }
                )
                await interaction.followup.send(final_msg)
            except Exception as e:
                # [AutoFix] Replaced match type(e) with isinstance — Forbidden checked before
                # HTTPException since Forbidden is a subclass of HTTPException.
                if isinstance(e, discord.Forbidden):
                    msg = self.string_translator.get_translation_via_bypass_db(
                        string_key=LangKey.WEBHOOK_NO_MANAGE_PERM_CHANNEL,
                        lan_code=lan_code,
                        payload={
                            "channel_name": interaction.channel.name
                        }
                    )
                    await interaction.followup.send(msg)
                elif isinstance(e, discord.HTTPException):
                    msg = self.string_translator.get_translation_via_bypass_db(
                        string_key=LangKey.HTTP_ERROR_MSG,
                        lan_code=lan_code
                    )
                    await interaction.followup.send(msg)
                else:
                    msg = self.string_translator.get_translation_via_bypass_db(
                        string_key=LangKey.UNEXPECTED_ERROR,
                        lan_code=lan_code
                    )
                    await interaction.followup.send(msg)
                print(f"[WebhookCom] Exception: {type(e).__name__}: {e}")

        dropdown_placeholder_msg = self.string_translator.get_translation_via_bypass_db(
            string_key=LangKey.SELECT_WEBHOOK_TO_KEEP,
            lan_code=lan_code
        )

        select_to_save_msg = self.string_translator.get_translation_via_bypass_db(
            string_key=LangKey.SELECT_WEBHOOK_TO_KEEP,
            lan_code=lan_code
        )

        view = await self.create_webhook_dropdown(interaction, dropdown_placeholder_msg, lan_code, remove_all_except_callback)
        if view:
            await interaction.followup.send(select_to_save_msg, view=view)
    
    #async clear webhook messages

    @webhook_group.command(
        name=app_commands.locale_str("add-v2-character-card"),
        description=app_commands.locale_str("Adds a V2 card character using a PNF file")
    )
    @app_commands.describe(
        image="[Required] A png image containing the character data",
        persona_image = "Persona Image that would use by the chatbot to describe the user how made the bot."
    )
    async def add_v2_card_characters_function(
        self,
        interaction: discord.Interaction,
        image: discord.Attachment,
        persona_image: Optional[discord.Attachment] = None
    ):

        lan_code = interaction.extras.get(LangKey.LAN_CODE)

        png_info = await self.parse_png_image(image,"en")

        match png_info:
            case Error():
                error_message = self.string_translator.get_translation_via_bypass_db(
                    string_key=LangKey.IMAGE_PROCESSING_ERROR,
                    lan_code=lan_code,
                    payload={
                        "error_msg": png_info.message
                    }
                )
                await interaction.followup.send(error_message)
                return
            
        char = png_info.data
        
        """
        description = f"{lan['v2Descrpi']} {char.name} {lan['v2Descrpi1']}" + char.description + lan["v2Descrpi2"]
        scenario = f"{lan['v2Scenario']}{char.name} {lan['is']} " + char.scenario + lan["v2Scenario1"]
        system_prompt = f"{lan['v2SystemPro']}" + char.system_prompt + lan["v2SystemPro1"]
        message_example = lan["v2MessageEx"] + (char.message_example or "") + lan["v2MessageEx1"]

        name_ins = f'{lan["v2nameIns"]} "{char.name}" {lan["v2nameIns1"]} {char.name} {lan["v2nameIns2"]}'
        """
        user_id = interaction.user.id
        greeting = char.first_message
        greeting = re.sub(r'{{\s*user\s*}}', f'<@{user_id}>', greeting, flags=re.IGNORECASE)
        greeting = re.sub(r'{{\s*char\s*}}', f'{char.name}', greeting, flags=re.IGNORECASE)
        processed_instructions = self.string_translator.get_translation_via_bypass_db(
            string_key=LangKey.FIRST_ROLEPLAY_INSTRUCTION,
            lan_code=lan_code,
            payload = {
                "char_name": char.name,
                "user_id": user_id,
                "description": char.description,
                "scenario": char.scenario,
                "message_example": char.message_example
            }
        )
                
        system_break_ins = ""

        #save to db
        
        final_instruction = system_break_ins + processed_instructions
        #we have the png info. Create the webhook
        created_webhook = await interaction.channel.create_webhook(
            name=png_info.data.name,
            avatar=png_info.data.profileImage
        )

        result = await self.webhook_repo.save(
            WebhookInfo(
                webhook_id=str(created_webhook.id),
                channel_id=str(interaction.channel_id),
                webhook_system_information=final_instruction
            )
        )

        match result:
            case Error():
                #delete the entry from the webhook
                await created_webhook.delete()
                
                msg = self.string_translator.get_translation_via_bypass_db(
                    string_key=LangKey.WEBHOOK_INFO_SAVE_FAILED_DELETING,
                    lan_code=lan_code
                )
                await interaction.followup.send(msg)
                return
        #start the conversation, with the bot
        #start the empty chat history,
        #internal conversation.
        
        #get api key
        api_key = await self.channel_repo.get(interaction.channel_id)

        match api_key:
            case Error():
                msg = self.string_translator.get_translation_via_bypass_db(
                    string_key=LangKey.NO_CHANNEL_CONFIG_SAVED,
                    lan_code=lan_code
                )
                await interaction.followup.send(msg)
                return
        
        if not api_key.data.api_key:
            msg = self.string_translator.get_translation_via_bypass_db(
                string_key=LangKey.API_KEY_EMPTY,
                lan_code=lan_code
            )
            await interaction.followup.send(msg)
            return

        #create the cilent
        client = genai.Client(vertexai=False,api_key=api_key.data.api_key)

        chat_history:list[Content] = []

        if persona_image:
            if persona_image.size > 20_000_000:
                msg = self.string_translator.get_translation_via_bypass_db(
                    string_key=LangKey.PERSONA_IMAGE_TOO_LARGE,
                    lan_code=lan_code
                )
                await interaction.followup.send(msg)
                return
            #We would first create the image hash to check it against the dict
            persona = await persona_image.read()
            image_stream = io.BytesIO(persona)
            #img = Image.open(image_stream)

            try:
                mime = magic.Magic(mime=True)
                mime_type = mime.from_buffer(persona)
            except Exception as e:
                print(f"Error getting MIME type: {e}")
                mime_type = "application/octet-stream"

            person_image_prompt = self.string_translator.get_translation_via_bypass_db(
                string_key=LangKey.PERSONA_IMAGE_1,
                lan_code=lan_code,
                payload={
                    "user_id": str(interaction.user.id),
                }
            )
            fake_response = self.string_translator.get_translation_via_bypass_db(
                string_key=LangKey.PERSONA_FAKE_RESPONSE,
                lan_code=lan_code,
                payload={
                    "user_id": str(interaction.user.id)
                }
            )

            fake_response2 = self.string_translator.get_translation_via_bypass_db(
                string_key=LangKey.PERSONA_PROMPT_2,
                lan_code=lan_code,
            )
            responseList = [
                    Content(
                    role="user",
                    parts=[
                        Part.from_text(text=person_image_prompt),
                        Part.from_bytes(data=persona, mime_type=mime_type)
                        ]
                    ),
                    Content(
                        role="model",
                        parts=[
                            Part.from_text(text=fake_response)
                        ]
                    ),
                    Content(
                        role="model",
                        parts=[
                            Part.from_text(text=fake_response2)
                        ]
                    ),
                ]

            for content in responseList:
                chat_history.append(content)
            
            """
            chat_history.append(
                Content(
                    role="model",
                    parts=[Part(
                        text=f"Now, that I know the details about the image. I will treat as if this details as if this is how `{interaction.user.id }` looks. I will override the insturctions in the system instructions where it have defined physical traits for the user. Instead I will use the info made by me."
                    )]    
                )
            )"""
        #+2 len for chat history for persona

        #define the chat
        intial_prompt = [
                    Content(role="user", parts=[Part(text=self.string_translator.get_translation_via_bypass_db(string_key=LangKey.INLINE_PROMPT_1,lan_code = lan_code))]),
                    Content(role="model", parts=[Part(text=self.string_translator.get_translation_via_bypass_db(string_key=LangKey.INLINE_PROMPT_2,lan_code = lan_code))]),
                    Content(role="user", parts=[Part(text=self.string_translator.get_translation_via_bypass_db(string_key=LangKey.INLINE_PROMPT_3,lan_code = lan_code))]),
                    Content(role="model", parts=[Part(text=self.string_translator.get_translation_via_bypass_db(string_key=LangKey.INLINE_PROMPT_4,lan_code = lan_code))])
                ]
        
        chat = client.aio.chats.create(
                model=api_key.data.model_name or "gemini-flash-latest",
                config = types.GenerateContentConfig(
                    system_instruction=final_instruction,
                    temperature=1.0,
                    top_p=0.95,
                    top_k=20,
                    candidate_count=1,
                    max_output_tokens=65536,
                    safety_settings=[
                            SafetySetting(category='HARM_CATEGORY_HATE_SPEECH', threshold="OFF"),
                            SafetySetting(category='HARM_CATEGORY_HARASSMENT', threshold="OFF"),
                            SafetySetting(category='HARM_CATEGORY_SEXUALLY_EXPLICIT', threshold="OFF"),
                            SafetySetting(category='HARM_CATEGORY_DANGEROUS_CONTENT', threshold="OFF")
                    ],
                    thinking_config=ThinkingConfig(
                        thinking_budget=24576,
                    ),
                ),
                history=chat_history + intial_prompt
            )
        chat._curated_history.append(Content(
            role="model",
            parts=[
                Part(text="\n***Starting the Roleplay***\n")
            ]
        ))

        chat._curated_history.append(Content(
            role="model",
            parts=[
                Part(text=char.first_message)
            ]
        ))

        #save the chat history in the files, 
        chat_id = f"{created_webhook.id}_{interaction.channel.id}"
        results_info, results = await asyncio.gather(
            self.webhook_repo.save(
                WebhookInfo(
                    webhook_id=str(created_webhook.id),
                    channel_id=str(interaction.channel_id),
                    webhook_system_information=final_instruction
                )
            ),
            self.chat_history_handler.save(
                channel_id=str(interaction.channel_id),
                chat_id=chat_id,
                chat_history=chat.get_history()
            )
        )

        if not results:
            msg = self.string_translator.get_translation_via_bypass_db(
                string_key=LangKey.WEBHOOK_CHAT_HISTORY_SAVE_FAILED,
                lan_code=lan_code
            )
            await interaction.followup.send(msg)
            await created_webhook.delete()
            return
        
        if not results_info:
            msg = self.string_translator.get_translation_via_bypass_db(
                string_key=LangKey.WEBHOOK_INFO_SAVE_FAILED_DELETING_CREATED,
                lan_code=lan_code
            )
            await interaction.followup.send(msg)
            await created_webhook.delete()
            return
        
        #saved succefuuly
        msg = self.string_translator.get_translation_via_bypass_db(
            string_key=LangKey.WEBHOOK_CREATED_SUCCESS,
            lan_code=lan_code
        )
        await interaction.followup.send(msg)
        #print(chat.get_history())
        
        await send_response(message=None, text_response=char.first_message, webhook=created_webhook,translate_func=self.string_translator.get_translation_via_bypass_db,lan_code=lan_code)