import asyncio
from pathlib import Path
from database.DatabaseManager import DatabaseManager
from database.repo.ChannelConfigRepo import ChannelConfigRepo
from database.repo.PersonaRepo import PersonaRepo
from database.repo.WebhookInfoRepo import WebhookInfoRepo
from database.repo.MediaHandlerRepo import MediaHandlerRepo
from PersonCache import PersonCache
from cogs.chat.ChatLock import ChatLock

class AppContainer:

    def __init__(self, db_path: Path = Path("./database/database.db")):
        self.db_path = db_path
        self.lock = ChatLock()
        self.db_manager = DatabaseManager(db_path)
        self.channel_config_repo = ChannelConfigRepo(db_path)
        self.persona_repo = PersonaRepo(db_path)
        self.webhook_info_repo = WebhookInfoRepo(db_path)
        self.media_handler_repo = MediaHandlerRepo(db_path)
        self.person_cache = PersonCache()

    def init(self):
        """Synchronously initializes the database. Blocks until tables are created."""
        asyncio.run(self.db_manager.init_database())