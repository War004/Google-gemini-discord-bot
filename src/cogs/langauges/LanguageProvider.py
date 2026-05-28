import json
from pathlib import Path


class LanguageProvider:
    def __init__(self, path: Path):
        self.path = path
        self.language_map = self._load_language_map()

    def _load_language_map(self) -> dict:
        lan_codes = [
            'as', 'bn', 'en', 'fr', 'gu', 'hi', 'ja',
            'kn', 'mai', 'mal', 'mni', 'mr', 'ne', 'ru', 'ta',
        ]

        language_map = {}
        for code in lan_codes:
            file_path = self.path / f"{code}String.json"
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    language_map[code] = json.load(f)
                    print(f"Loaded language: {code}")
            except FileNotFoundError:
                print(f"Warning: Language file not found: {file_path}")
            except json.JSONDecodeError:
                print(f"Warning: Invalid JSON in language file: {file_path}")
        return language_map