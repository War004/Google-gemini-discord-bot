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
from src.cogs.chat.ChatHistoryHandler import ChatHistoryHandler
from src.translator.base_translator import BaseTranslator

class AppContainer:

    def __init__(self, api_bloom: BloomFilter, lan_bloom: BloomFilter, chat_history_base_path: Path, translation: BaseTranslator, db_path: Path = Path("./database/database.db")):
        self.db_path = db_path
        self.chat_history_handler = ChatHistoryHandler(chat_history_base_path)
        self.lock = ChatLock()
        self.db_manager = DatabaseManager(db_path)
        self.channel_config_repo = ChannelConfigRepo(db_path,api_bloom,lan_bloom,translation)
        self.persona_repo = PersonaRepo(db_path,translation)
        self.webhook_info_repo = WebhookInfoRepo(db_path,translation)
        self.media_handler_repo = MediaHandlerRepo(db_path,translation)
        self.person_cache = PersonCache()

    def init(self):
        """Synchronously initializes the database. Blocks until tables are created."""
        asyncio.run(self.db_manager.init_database())