import aiosqlite
import sqlite3
from pathlib import Path
from loader.Results import Success, Error
from database.domain.MediaHandler import MediaHandler


class MediaHandlerDao:

    def __init__(self, db_path: Path):
        self.db_path = db_path

    # ── Core methods ──────────────────────────────────────────────

    async def save(self, media: MediaHandler) -> Success[MediaHandler] | Error:
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
                return Error(
                    message="Channel entry doesn't exist.", 
                    solution="The solution is to add an API key first.",
                    exception=e
                )
            return Error(message="Failed to save media handler entry due to integrity error", exception=e)
        except Exception as e:
            return Error(message="Failed to save media handler entry", exception=e)

    async def delete(self, chat_id: str) -> Success[bool] | Error:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "DELETE FROM media_handler WHERE chat_id = ?",
                    (chat_id,),
                )
                await db.commit()
                if cursor.rowcount == 0:
                    return Error(message="Media handler entry not found", code=404)
            return Success(data=True)
        except Exception as e:
            return Error(message="Failed to delete media handler entry", exception=e)

    async def get(self, chat_id: str) -> Success[MediaHandler] | Error:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT * FROM media_handler WHERE chat_id = ?",
                    (chat_id,),
                )
                row = await cursor.fetchone()
                if row is None:
                    return Error(message="Media handler entry not found", code=404)
                media = MediaHandler(
                    chat_id=row["chat_id"],
                    channel_id=row["channel_id"],
                    timestamp=row["timestamp"],
                    index_in_history=row["index_in_history"],
                )
            return Success(data=media)
        except Exception as e:
            return Error(message="Failed to get media handler entry", exception=e)

    # ── Bulk / query methods ──────────────────────────────────────

    async def get_by_channel(self, channel_id: str) -> Success[list[MediaHandler]] | Error:
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
            return Error(message="Failed to get media entries by channel", exception=e)

    async def delete_by_channel(self, channel_id: str) -> Success[int] | Error:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "DELETE FROM media_handler WHERE channel_id = ?",
                    (channel_id,),
                )
                await db.commit()
            return Success(data=cursor.rowcount)
        except Exception as e:
            return Error(message="Failed to delete media entries by channel", exception=e)

    async def get_expired(self, before_timestamp: int) -> Success[list[MediaHandler]] | Error:
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
            return Error(message="Failed to get expired media entries", exception=e)

    async def get_expired_by_chat_id(self, chat_id: str, before_timestamp: int) -> Success[list[MediaHandler]] | Error:
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
            return Error(message="Failed to get expired media entries by chat id", exception=e)

    async def delete_expired(self, before_timestamp: int) -> Success[int] | Error:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "DELETE FROM media_handler WHERE timestamp < ?",
                    (before_timestamp,),
                )
                await db.commit()
            return Success(data=cursor.rowcount)
        except Exception as e:
            return Error(message="Failed to delete expired media entries", exception=e)
