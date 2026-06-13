import aiosqlite
import sqlite3
from pathlib import Path
from src.loader.Results import Success
from database.domain.MediaHandler import MediaHandler
from database.exceptions.database_exception import MediaHandlerNotFoundError, ChannelNotFoundError,MediaHandlerIntegrityError,MediaHandlerDatabaseError


class MediaHandlerDao:

    def __init__(self, db_path: Path):
        self.db_path = db_path

    # ── Core methods ──────────────────────────────────────────────

    async def save(self, media: MediaHandler) -> Success[MediaHandler]:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("PRAGMA foreign_keys = ON;")
                await db.execute(
                    """INSERT OR REPLACE INTO media_handler
                       (chat_id, channel_id, timestamp, index_in_history)
                       VALUES (?, ?, ?, ?)""",
                    (
                        media.chat_id,
                        media.channel_id,
                        media.timestamp,
                        media.index_in_history,
                    ),
                )
                await db.commit()
            return Success(data=media)
        except sqlite3.IntegrityError as e:
            if "FOREIGN KEY constraint failed" in str(e):
                raise ChannelNotFoundError() from e
            raise MediaHandlerIntegrityError() from e
        except Exception as e:
            raise MediaHandlerDatabaseError() from e

    async def delete(self, chat_id: str) -> Success[bool]:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "DELETE FROM media_handler WHERE chat_id = ?",
                    (chat_id,),
                )
                await db.commit()
                if cursor.rowcount == 0:
                    raise MediaHandlerNotFoundError()
            return Success(data=True)
        except MediaHandlerNotFoundError:
            raise
        except Exception as e:
            raise MediaHandlerDatabaseError() from e

    async def get(self, chat_id: str) -> Success[MediaHandler]:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT * FROM media_handler WHERE chat_id = ?",
                    (chat_id,),
                )
                row = await cursor.fetchone()
                if row is None:
                    raise MediaHandlerNotFoundError()
                media = MediaHandler(
                    chat_id=row["chat_id"],
                    channel_id=row["channel_id"],
                    timestamp=row["timestamp"],
                    index_in_history=row["index_in_history"],
                )
            return Success(data=media)
        except MediaHandlerNotFoundError:
            raise
        except Exception as e:
            raise MediaHandlerDatabaseError() from e

    # ── Bulk / query methods ──────────────────────────────────────

    async def get_by_channel(self, channel_id: str) -> Success[list[MediaHandler]]:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT * FROM media_handler WHERE channel_id = ?",
                    (channel_id,),
                )
                rows = await cursor.fetchall()
                items = [
                    MediaHandler(
                        chat_id=row["chat_id"],
                        channel_id=row["channel_id"],
                        timestamp=row["timestamp"],
                        index_in_history=row["index_in_history"],
                    )
                    for row in rows
                ]
            return Success(data=items)
        except Exception as e:
            raise MediaHandlerDatabaseError() from e

    async def delete_by_channel(self, channel_id: str) -> Success[int]:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "DELETE FROM media_handler WHERE channel_id = ?",
                    (channel_id,),
                )
                await db.commit()
            return Success(data=cursor.rowcount)
        except Exception as e:
            raise MediaHandlerDatabaseError() from e

    async def get_expired(self, before_timestamp: int) -> Success[list[MediaHandler]]:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT * FROM media_handler WHERE timestamp < ?",
                    (before_timestamp,),
                )
                rows = await cursor.fetchall()
                items = [
                    MediaHandler(
                        chat_id=row["chat_id"],
                        channel_id=row["channel_id"],
                        timestamp=row["timestamp"],
                        index_in_history=row["index_in_history"],
                    )
                    for row in rows
                ]
            return Success(data=items)
        except Exception as e:
            raise MediaHandlerDatabaseError() from e

    async def get_expired_by_chat_id(self, chat_id: str, before_timestamp: int) -> Success[list[MediaHandler]]:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT * FROM media_handler WHERE chat_id = ? AND timestamp < ?",
                    (chat_id, before_timestamp),
                )
                rows = await cursor.fetchall()
                items = [
                    MediaHandler(
                        chat_id=row["chat_id"],
                        channel_id=row["channel_id"],
                        timestamp=row["timestamp"],
                        index_in_history=row["index_in_history"],
                    )
                    for row in rows
                ]
            return Success(data=items)
        except Exception as e:
            raise MediaHandlerDatabaseError() from e

    async def delete_expired(self, before_timestamp: int) -> Success[int]:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "DELETE FROM media_handler WHERE timestamp < ?",
                    (before_timestamp,),
                )
                await db.commit()
            return Success(data=cursor.rowcount)
        except Exception as e:
            raise MediaHandlerDatabaseError() from e