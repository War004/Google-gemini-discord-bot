import aiosqlite
from pathlib import Path

class DatabaseManager:
    def __init__(self, db_path: Path = Path(r"database.db")):
        self.db_path = db_path

    async def init_database(self):
        """Creates the .db file and builds the tables."""
        async with aiosqlite.connect(self.db_path) as db:
            # Turn on Foreign Keys
            await db.execute("PRAGMA foreign_keys = ON;")
            
            #1st table for channel config
            await db.execute("""
                CREATE TABLE IF NOT EXISTS channel_config (
                    channel_id TEXT PRIMARY KEY,
                    api_key TEXT,
                    model_name TEXT,
                    default_lan_code TEXT,
                    r18_enabled BOOLEAN DEFAULT 0
                )
            """)

            #2nd table for persona management 
            await db.execute("""
                CREATE TABLE IF NOT EXISTS persona (
                    hash TEXT PRIMARY KEY,
                    information TEXT
                )
            """)

            #3rd table for webhook system promot managmenet=
            await db.execute("""
                CREATE TABLE IF NOT EXISTS webhook_info (
                    bot_id INTEGER PRIMARY KEY,
                    channel_id TEXT,
                    bot_info TEXT,
                    FOREIGN KEY (channel_id) REFERENCES channel_config (channel_id) ON DELETE CASCADE
                )
            """)

            #4th table for the media handler
            await db.execute("""
                CREATE TABLE IF NOT EXISTS media_handler (
                    chat_id TEXT PRIMARY KEY,
                    channel_id TEXT,
                    timestamp INTEGER,
                    index_in_history INTEGER,
                    FOREIGN KEY (channel_id) REFERENCES channel_config (channel_id) ON DELETE CASCADE

                )
            """)
            await db.commit()
            print("Database initialized successfully!")