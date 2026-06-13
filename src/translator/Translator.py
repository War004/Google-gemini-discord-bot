import json
import discord
from discord import app_commands
from pathlib import Path
from database.repo.ChannelConfigRepo import ChannelConfigRepo
from src.BloomFilter import BloomFilter
from src.loader.Results import Success, Error
from src.translator.base_translator import BaseTranslator

class Translator(BaseTranslator,app_commands.Translator):
    def __init__(self, path: Path, channel_repo: ChannelConfigRepo, lan_bloom: BloomFilter):
        super().__init__(path)
        self.channel_repo_instance: ChannelConfigRepo | None = None
        self.lan_bloom: BloomFilter = lan_bloom
        self.discord_locale_map = {
            discord.Locale.american_english: "en",
            discord.Locale.british_english: "en",
            discord.Locale.french: "fr",
            discord.Locale.hindi: "hi",
            discord.Locale.japanese: "ja",
            discord.Locale.russian: "ru",
        }

    def set_channel_repo(self, channel_repo: ChannelConfigRepo):
        self.channel_repo = channel_repo
        
    async def translate_text(self, channel_id: str, string_key: str, payload: dict[str,str] | None = None, direct_message:str| None = None, default_lan_code: str | None = None) -> str:
        if(direct_message is not None):
            return direct_message
        default = lambda: self._get_translation_(string_key, default_lan_code or "en", payload)

        if not self.lan_bloom.check(channel_id):
            return default()

        results = await self.channel_repo_instance.get(channel_id)

        match results:
            case Success():
                #generally the value of data won't be null, as when the user add an lan or an api key
                #you can remove it, but only modify it.
                #still one more barrier to unexpected behvaior. Need to implement in other function that access db
                if results.data is None:
                    return default()
                return self._get_translation_(string_key, results.data.default_lan_code, payload or {})

            case Error():
                print(f"Error while getting the db value: {results.message}")
                return default()
    
    async def translate(self, string: app_commands.locale_str, locale: discord.Locale, context: app_commands.TranslationContext) -> str | None:
        
        internal_lan_code = self.discord_locale_map.get(locale)
        if not internal_lan_code:
            return None

        # This will safely return None if the translation is missing from the JSON
        language_dict = self._get_lan_map(internal_lan_code)
        translated_string = language_dict.get(string.message)

        # Only apply formatting if a translation actually exists
        if translated_string:
            locations_requiring_formatting = [
                app_commands.TranslationContextLocation.command_name,
                app_commands.TranslationContextLocation.group_name,
                app_commands.TranslationContextLocation.parameter_name
            ]
            
            # If the string is a command/group/parameter name, forcefully clean it
            if context.location in locations_requiring_formatting:
                translated_string = translated_string.lower().replace(" ", "_")
                translated_string = translated_string[:32] # Force max 32 characters

        return translated_string