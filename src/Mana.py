import logging

import discord
import asyncio
import sys
from discord.ext import commands

from src.cogs.chat.MessageProcessor import MessageProcessor
from src.cogs.chat.ResponseHandler import send_response
from database.repo.WebhookInfoRepo import WebhookInfoRepo
from database.repo.ChannelConfigRepo import ChannelConfigRepo
from src.loader.Results import Success, Error
from src.BloomFilter import BloomFilter
from src.loader.Results import Success, Error
from src.translator.translator import Translator as TranslatorService
from src.translator.lan_key import LangKey
logger = logging.getLogger(__name__)


class Mana(commands.Bot):
    """
    message provider
    api repo
    webhook repo
    chat history handler
    lanaguge kety 
    """
    def __init__(
        self,
        command_prefix,
        intents,
        string_translation_service: TranslatorService,
        message_processor: MessageProcessor,
        webhook_repo: WebhookInfoRepo,
        channel_config_repo: ChannelConfigRepo,
        api_bloom: BloomFilter,
        lan_bloom: BloomFilter
    ):
        super().__init__(command_prefix=command_prefix, intents=intents)
        self.string_translator_service = string_translation_service
        self.message_processor = message_processor
        self.webhook_repo = webhook_repo
        self.channel_config_repo = channel_config_repo
        self.api_bloom = api_bloom
        self.lan_bloom = lan_bloom
        self.webhook_slash_command = None
        self.config_slash_command = None
        self.common_slash_command = None

    async def setup_hook(self):
        if self.webhook_slash_command:
            await self.add_cog(self.webhook_slash_command)
            print("Adding webhook slash commands")
        if self.config_slash_command:
            await self.add_cog(self.config_slash_command)
            print("Adding config slash commands")
        if self.common_slash_command:
            await self.add_cog(self.common_slash_command)
            print("Adding common slash commands")
        await self.tree.set_translator(self.string_translator_service)
            
        try:
            synced_commands = await self.tree.sync()
            print(f"Successfully synced {len(synced_commands)} commands globally!")
        except Exception as e:
            print(f"Failed to sync commands: {e}")

    async def on_ready(self):
        print(f"Logged in as {self.user} (ID: {self.user.id})")
        print(f"Connected to {len(self.guilds)} guilds.")
        total_member = 0
        #loop and fill the values for default server local
        for guild in self.guilds:
            member_count = sum(1 for member in guild.members if not member.bot)
            print(f"\nServer Name:{guild.name}: Member Count: {member_count}")
            total_member += member_count
        print(f"\nTotal memeber: {total_member}\n")

        #Hydrating the api bloom and language bloom using channel config repo
        api_channel, lan_channel = await asyncio.gather(
            self.channel_config_repo.get_channels_with_api_key(),
            self.channel_config_repo.get_channels_with_lan_code()
        )

        match api_channel:
            case Success():
                if isinstance(lan_channel,Success):
                    print("Filling the api bloom")
                    for entry in api_channel.data:
                        self.api_bloom.add(entry)

                    print("Filling the lan bloom")
                    for entry in lan_channel.data:
                        self.lan_bloom.add(entry)
                else:
                    print("Not able to fill the lan bloom")
                    print(lan_channel.message)
                    print(lan_channel.exception)
                    sys.exit(1)

            case Error():
                print("Not able to fill the api bloom")
                print(api_channel.message)
                print(api_channel.exception)
                sys.exit(1)
                


    """
    async def on_guild_update(self, before:discord.Guild, after:discord.Guild):
    """
    async def on_message(self, message: discord.Message) -> None:
        #start_time = time.perf_counter()
        if message.author == self.user:
            return
        # Ignore messages from webhooks (prevent self-loops)
        if message.webhook_id:
            return

        # Check if this is a reply to a webhook character
        webhook = await self._get_replied_webhook(message)
        if webhook and webhook.user == self.user:
            guild_prefered_lan_code = message.guild.preferred_locale.value.split("-")[0]
            channel_id = str(message.channel.id)
            # Check API key here if webhook communication also requires it
            if self.api_bloom.check(channel_id) == False:
                # first db hit happens here,
                # thought to use the channel config to get the whole channel config(with the lan code)
                # but this function doesn't need api key and model name.
                # therfore keep this as it is, one additional db hit is fine at the current scale
                # suggestion would be using a dict as cahche in the repo
                lan_code_wrapper = await self.channel_config_repo.get_lan_code(
                    channel_id=message.channel.id,
                    lan_code=guild_prefered_lan_code #This is the entry point, if the db load fails we need to use local prefer
                )
                match lan_code_wrapper:
                    case Success():
                        lan_code = lan_code_wrapper.data or guild_prefered_lan_code
                    case Error():
                        lan_code = guild_prefered_lan_code
                
                string_message = self.string_translator_service.get_translation_via_bypass_db(
                    string_key=LangKey.NO_API,
                    lan_code=lan_code
                )

                await message.reply(string_message)
                return
            await self._handle_webhook_message(message, webhook)
            return
        
        # Respond to mentions and DMs (main bot)
        is_mention = self.user in message.mentions
        is_dm = isinstance(message.channel, discord.DMChannel)

        if is_mention or is_dm:
            guild_prefered_lan_code = message.guild.preferred_locale.split("-")[0] if message.guild else "en"
            # Only check the API key if the bot is actually being addressed
            if self.api_bloom.check(str(message.channel.id)) == False:
                lan_code_wrapper = await self.channel_config_repo.get_lan_code(
                    channel_id=message.channel.id,
                    lan_code=guild_prefered_lan_code #This is the entry point, if the db load fails we need to use local prefer
                )
                match lan_code_wrapper:
                    case Success():
                        lan_code = lan_code_wrapper.data or guild_prefered_lan_code
                    case Error():
                        lan_code = guild_prefered_lan_code

                string_message = self.string_translator_service.get_translation_via_bypass_db(
                    string_key=LangKey.NO_API,
                    lan_code=lan_code
                )
                await message.reply(string_message)
                #end_time = time.perf_counter()
                #elapsed_time = end_time - start_time
                #print(f"The function took {elapsed_time:.4f} seconds to complete.")
                return
                
            await self._handle_message(message)
            #end_time = time.perf_counter()
            #elapsed_time = end_time - start_time
            #print(f"The function took {elapsed_time:.4f} seconds to complete.")
        # await self.process_commands(message)

    async def _get_replied_webhook(self, message: discord.Message) -> discord.Webhook | None:
        """
        If the message is a reply to a bot-created webhook, returns that webhook.
        Returns None otherwise.
        """
        if not message.reference or not message.reference.message_id:
            return None

        # 1. Check the local cache FIRST to avoid rate limits
        replied_msg = message.reference.resolved

        # 2. If it's not in the cache (and hasn't been deleted), fetch it from the API
        if replied_msg is None and not isinstance(replied_msg, discord.DeletedReferencedMessage):
            try:
                replied_msg = await message.channel.fetch_message(message.reference.message_id)
            except (discord.NotFound, discord.HTTPException):
                return None
        
        # If it was deleted or we still couldn't get it, bail out
        if not replied_msg or isinstance(replied_msg, discord.DeletedReferencedMessage):
            return None

        # Check if the replied message was sent by a webhook
        if not replied_msg.webhook_id:
            return None

        # Verify it's one of our webhooks (exists in our store)
        result = await self.webhook_repo.get_by_webhook_id(replied_msg.webhook_id)

        match result:
            case Error():
                print(f"Error: {result.message}")
                print(f"message: {message.content}")
                return None

        # Fetch the actual webhook object for sending
        try:
            webhook = await self.fetch_webhook(replied_msg.webhook_id)
            return webhook
        except (discord.NotFound, discord.HTTPException):
            logger.warning("Could not fetch webhook %s", replied_msg.webhook_id)
            return None

    async def _handle_message(self, message: discord.Message) -> None:
        """Handles a main-bot message with locking and reaction indicator."""

        try:
            text_response, image_data = await self.message_processor.process(message = message, bot_user=self.user)
            await send_response(message, text_response, image_data)

        except Exception as e:
            logger.error("Error handling message %d: %s", message.id, e)
            await message.channel.send(
                f"<@{message.author.id}> ❌ An error occurred:\n```{str(text_response)}```"
            )

        finally:
            pass

    async def _handle_webhook_message(
        self, message: discord.Message, webhook: discord.Webhook
    ) -> None:
        """Handles a message directed at a webhook character."""

        try:
            text_response, image_data = await self.message_processor.process(
                message,bot_user = self.user, webhook_id=str(webhook.id)
            )
            await send_response(message, text_response, image_data, webhook=webhook)

        except Exception as e:
            # logger.exception automatically appends the full traceback to the log
            logger.exception("Error handling webhook message %d", message.id)
            
            # Keep the Discord message clean so it doesn't spam the channel with code
            await message.channel.send(
                f"<@{message.author.id}> ❌ An error occurred with {webhook.name}:\n```{str(e)}```"
            )
            
        finally:
            pass