import discord
from discord import app_commands, Locale
from database.repo.ChannelConfigRepo import ChannelConfigRepo
from BloomFilter import BloomFilter
from loader.Results import Success, Error

class Translator(app_commands.Translator):
    """
    A custom translation class that handles Discord's native UI localization
    and retrieves the correct language code for bot replies based on database preferences.
    """

    def __init__(
        self, 
        channel_config_repo: ChannelConfigRepo,
        lan_channel_entry_bloom_filter: BloomFilter,
        server_default_lan: dict[str,str],
        language_map: dict
    ):
        """
        Initializes the Translator with the required database and memory tools.

        :param channel_config_repo: The repository used to query the database for channel-specific language settings.
        :param lan_channel_entry_bloom_filter: The Bloom filter used to gatekeep database queries.
        :param language_map: A dictionary containing all the translated strings.
        """
        self.channel_config_repo = channel_config_repo
        self.bloom_filter_channel_entry = lan_channel_entry_bloom_filter
        self.server_default_lan = server_default_lan
        self.language_map = language_map
    
    # --- 1. DISCORD UI TRANSLATION ---
    async def translate(
        self, 
        string: app_commands.locale_str, 
        locale: discord.Locale, 
        context: app_commands.TranslationContext
    ) -> str | None:
        """
        Automatically called by discord.py during `tree.sync()` to translate command UI elements.
        """
        lang_code = locale.value
        
        # Check if we support this language, and safely attempt to get the translated word
        if lang_code in self.language_map:
            return self.language_map[lang_code].get(string.message)
            
        return None

    # --- 2. BOT REPLY TRANSLATION (Normal Messages) ---
    async def get_lan_code_norm(self, server_id: str,channel_id: str) -> str:
        """
        Retrieves the correct language code for standard text channel messages 
        based on the database settings.

        :param channel_id: The ID of the Discord channel where the message was sent.
        :return: The language code string (e.g., "en", "es-ES"). Defaults to "en".
        """
        if self.bloom_filter_channel_entry.check(channel_id):
            result = await self.channel_config_repo.get(channel_id)

            match result:
                case Success():
                    return result.data.default_lan_code
                case Error():
                    print(f"Translator Warning (get_lan_code_norm): {result.message}")
        else:
            return self.server_default_lan.get(server_id,"en")
    
    # --- 3. BOT REPLY TRANSLATION (Slash Commands) ---
    async def get_lan_code_slash(
        self,
        server_id:str,
        channel_id: str, 
        user_locale: Locale | None
    ) -> str:
        """
        Retrieves the correct language code for slash command responses, prioritizing
        database settings, and falling back to the user's personal app language.

        :param channel_id: The ID of the Discord channel where the command was executed.
        :param user_locale: The user's personal Discord app language setting (from interaction.locale).
        :return: The language code string (e.g., "en", "es-ES"). Defaults to "en".
        """
        if self.bloom_filter_channel_entry.check(channel_id):
            result = await self.channel_config_repo.get(channel_id)

            match result:
                case Success():
                    return result.data.default_lan_code
                case Error():
                    print(f"Translator Warning (get_lan_code_slash): {result.message}")
        
        # If Bloom filter says no, or database query fails, fall back to user locale
        return user_locale.value if user_locale else self.server_default_lan.get(server_id,"en")