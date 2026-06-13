import json
from pathlib import Path

class BaseTranslator:
    def __init__(self, path: Path):
        self.path = path
        self.language_map:dict[str,dict[str,str]] = self._load_language_map()
    

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
        
        self._check_inconsistent_map(language_map)
        return language_map
    
    def _check_inconsistent_map(
        self,
        lan_map: dict[str, dict[str, str]],
        extra_info: bool = False,
        base_map_code: str = "en"
    ):
        # Get the base map
        base_lan_map: dict[str, str] = lan_map.get(base_map_code)
        key_checker_set = set()

        if base_lan_map is None:
            print(f"Warning: cannot find the lan map for the base condition '{base_map_code}'.")
            return

        for key in base_lan_map:
            key_checker_set.add(key)

        if len(key_checker_set) == 0:
            print(f"The base lan map '{base_map_code}' is empty — translation might not work correctly.")
            return

        for maps in lan_map:
            different_keys = 0
            if maps != base_map_code:
                for key in lan_map[maps].keys():
                    if key not in key_checker_set:
                        different_keys += 1
                        if extra_info:
                            print(f"In '{maps}':")
                            print(f"  Missing key: '{key}'")

                print(f"Found {different_keys} inconsistent key(s) in '{maps}'")
        
        print("Checked the translation values")
    
    def _get_lan_map(self,lan_code:str) -> dict[str,str]:
        return self.language_map.get(lan_code, self.language_map["en"])
    
    def reload(self):
        self.language_map = self._load_language_map()

    def get_translation_via_bypass_db(self,string_key:str,lan_code:str,payload:dict[str,str] = {} ,direct_message: str | None = None) -> str:
        if direct_message:
            return direct_message
        
        return self._get_translation_(
            string_key,
            lan_code,
            payload
        )
        
    def _get_translation_(self,string_key:str,lan_code:str,payload:dict[str,str]) -> str:
        language = self.language_map.get(lan_code, self.language_map["en"])
        string_value = language.get(string_key) or self.language_map["en"][string_key]
        try:
            return string_value.format(**payload)
        except KeyError as e:
            print(f"Error: Missing variable {e} in payload for string: '{string_value}'")
            return string_value