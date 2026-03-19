import logging

import discord
from discord.ext import commands

from cogs.chat.MessageProcessor import MessageProcessor
from cogs.chat.ResponseHandler import send_response
from database.repo.WebhookInfoRepo import WebhookInfoRepo
from loader.Results import Error

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
        message_processor: MessageProcessor,
        webhook_repo: WebhookInfoRepo,
        language_map: dict[str, str],
        server_default_lan: dict[str,str]
    ):
        super().__init__(command_prefix=command_prefix, intents=intents)
        self.message_processor = message_processor
        self.webhook_repo = webhook_repo
        self.language_map = language_map
        self.server_default_lan = server_default_lan
        self.webhook_slash_command = None
        self.config_slash_command = None

    async def setup_hook(self):
        if self.webhook_slash_command:
            await self.add_cog(self.webhook_slash_command)
            print("Adding webhook slash commands")
        if self.config_slash_command:
            await self.add_cog(self.config_slash_command)
            print("Adding config slash commands")
            
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
            self.server_default_lan[str(guild.id)] = guild.preferred_locale.value
            member_count = sum(1 for member in guild.members if not member.bot)
            print(f"\nServer Name:{guild.name}: Member Count: {member_count}")
            total_member += member_count
        print(f"\nTotal memeber: {total_member}\n")

    async def on_guild_update(self, before:discord.Guild, after:discord.Guild):
        if before.preferred_locale != after.preferred_locale:
            self.server_default_lan[str(after.id)] = after.preferred_locale

    async def on_message(self, message: discord.Message) -> None:
        if message.author == self.user:
            return
        # Ignore messages from webhooks (prevent self-loops)
        if message.webhook_id:
            return

        # Check if this is a reply to a webhook character
        webhook = await self._get_replied_webhook(message)
        if webhook and webhook.user == self.user:
            await self._handle_webhook_message(message, webhook)
            #await self.process_commands(message)
            return

        # Respond to mentions and DMs (main bot)
        is_mention = self.user in message.mentions
        is_dm = isinstance(message.channel, discord.DMChannel)

        if is_mention or is_dm:
            await self._handle_message(message)

        #await self.process_commands(message)

    async def _get_replied_webhook(self, message: discord.Message) -> discord.Webhook | None:
        """
        If the message is a reply to a bot-created webhook, returns that webhook.
        Returns None otherwise.
        """
        if not message.reference or not message.reference.message_id:
            return None

        try:
            replied_msg = await message.channel.fetch_message(message.reference.message_id)
        except (discord.NotFound, discord.HTTPException):
            return None

        # Check if the replied message was sent by a webhook we manage
        if not replied_msg.webhook_id:
            return None

        # Verify it's one of our webhooks (exists in our store)
        result = await self.webhook_repo.get_by_webhook_id(replied_msg.webhook_id)

        match result:
            case Error():
                print(f"Error: {result.message}")
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
            #don't use e, as it uses chat_id??
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