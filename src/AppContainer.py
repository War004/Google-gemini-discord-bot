import asyncio
from pathlib import Path
from database.DatabaseManager import DatabaseManager
from database.repo.ChannelConfigRepo import ChannelConfigRepo
from database.repo.PersonaRepo import PersonaRepo
from database.repo.WebhookInfoRepo import WebhookInfoRepo
from database.repo.MediaHandlerRepo import MediaHandlerRepo
from src.PersonCache import PersonCache
from src.cogs.chat.ChatLock import ChatLock
from src.BloomFilter import BloomFilter

class AppContainer:

    def __init__(self, api_bloom: BloomFilter, lan_bloom: BloomFilter, db_path: Path = Path("./database/database.db")):
        self.db_path = db_path
        self.lock = ChatLock()
        self.db_manager = DatabaseManager(db_path)
        self.channel_config_repo = ChannelConfigRepo(db_path,api_bloom,lan_bloom)
        self.persona_repo = PersonaRepo(db_path)
        self.webhook_info_repo = WebhookInfoRepo(db_path)
        self.media_handler_repo = MediaHandlerRepo(db_path)
        self.person_cache = PersonCache()

    def init(self):
        """Synchronously initializes the database. Blocks until tables are created."""
        asyncio.run(self.db_manager.init_database())