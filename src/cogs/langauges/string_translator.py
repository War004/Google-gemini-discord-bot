import json
from pathlib import Path
from database.repo.ChannelConfigRepo import ChannelConfigRepo
from src.BloomFilter import BloomFilter
from src.loader.Results import Success, Error

class StringTranslator:
    def __init__(self, path: Path, channel_repo: ChannelConfigRepo, lan_bloom: BloomFilter):
        self.path = path
        self.language_map:dict[str,dict[str,str]] = self._load_language_map()
        self.channel_repo_instance: ChannelConfigRepo = channel_repo
        self.lan_bloom: BloomFilter = lan_bloom

    def _load_language_map(self) -> dict:
        lan_codes:list[str] = [
            'as', 'bn', 'en', 'fr', 'gu', 'hi', 'ja',
            'kn', 'mai', 'mal', 'mni', 'mr', 'ne', 'ru', 'ta',
        ]

        language_map:dict[str,dict[str,str]] = {}

        for code in lan_codes:
            file_path = "data" / self.path / f"{code}String.json"
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    language_map[code] = json.load(f)
                    print(f"Loaded language: {code}")
            except FileNotFoundError:
                print(f"Warning: Language file not found: {file_path}")
            except json.JSONDecodeError:
                print(f"Warning: Invalid JSON in language file: {file_path}")
        return language_map
    
    def reload(self):
        self.language_map = self._load_language_map()

    async def translate_text(self, channel_id: str, string_key: str, lan_code: str, payload: list[str], direct_message:str| None = None) -> str:
        if(direct_message is not None):
            return direct_message
        default = lambda: self._get_translation_(string_key, "en", payload)

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
                return self._get_translation_(string_key, results.data.default_lan_code, payload)

            case Error():
                print(f"Error while getting the db value: {results.message}")
                return default()
        
    def _get_translation_(self,string_key:str,lan_code:str,payload:list[str]) -> str:
        language = self.language_map.get(lan_code, self.language_map["en"])
        string_value = language.get(string_key) or self.language_map["en"][string_key]

        return string_value.format(*payload)