from pathlib import Path
from loader.Json import Json
"""
Log formatting:
"""
json_loader = Json()

class Constants:
    def __init__(self, ram_mode: bool = False):
        self.ram_only_mode = ram_mode
        self.chat_folder_path = None if ram_mode else Path("./chat")
        self.api_direct_path = None if ram_mode else Path("./api/apiJson.json")
        self.media_folder_path = None if ram_mode else (self.chat_folder_path / "media")