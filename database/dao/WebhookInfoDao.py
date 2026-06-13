import aiosqlite
import sqlite3
from pathlib import Path
from src.loader.Results import Success
from database.domain.WebhookInfo import WebhookInfo
from database.exceptions.database_exception import ChannelNotFoundError,WebhookNotFoundError,WebhookIntegrityError,WebhookDatabaseError


class WebhookInfoDao:

    def __init__(self, db_path: Path):
        self.db_path = db_path

    # ── Core methods ──────────────────────────────────────────────

    async def save(self, webhook_info: WebhookInfo) -> Success[WebhookInfo]:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("PRAGMA foreign_keys = ON;")
                await db.execute(
                    """INSERT OR REPLACE INTO webhook_info
                       (bot_id, channel_id, bot_info)
                       VALUES (?, ?, ?)""",
                    (
                        webhook_info.webhook_id,
                        webhook_info.channel_id,
                        webhook_info.webhook_system_information,
                    ),
                )
                await db.commit()
            return Success(data=webhook_info)
        except sqlite3.IntegrityError as e:
            if "FOREIGN KEY constraint failed" in str(e):
                raise ChannelNotFoundError() from e
            raise WebhookIntegrityError() from e
        except Exception as e:
            raise WebhookDatabaseError() from e

    async def delete(self, bot_id: int) -> Success[bool]:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "DELETE FROM webhook_info WHERE bot_id = ?",
                    (bot_id,),
                )
                await db.commit()
                if cursor.rowcount == 0:
                    raise WebhookNotFoundError()
            return Success(data=True)
        except WebhookNotFoundError:
            raise
        except Exception as e:
            raise WebhookDatabaseError() from e

    async def get(self, bot_id: int) -> Success[WebhookInfo]:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT * FROM webhook_info WHERE bot_id = ?",
                    (bot_id,),
                )
                row = await cursor.fetchone()
                if row is None:
                    raise WebhookNotFoundError()
                info = WebhookInfo(
                    webhook_id=row["bot_id"],
                    channel_id=row["channel_id"],
                    webhook_system_information=row["bot_info"],
                )
            return Success(data=info)
        except WebhookNotFoundError:
            raise
        except Exception as e:
            raise WebhookDatabaseError() from e

    # ── Bulk / query methods ──────────────────────────────────────

    async def get_by_channel(self, channel_id: str) -> Success[list[WebhookInfo]]:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT * FROM webhook_info WHERE channel_id = ?",
                    (channel_id,),
                )
                rows = await cursor.fetchall()
                items = [
                    WebhookInfo(
                        webhook_id=row["bot_id"],
                        channel_id=row["channel_id"],
                        webhook_system_information=row["bot_info"],
                    )
                    for row in rows
                ]
            return Success(data=items)
        except Exception as e:
            raise WebhookDatabaseError() from e

    async def delete_by_channel(self, channel_id: str) -> Success[int]:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "DELETE FROM webhook_info WHERE channel_id = ?",
                    (channel_id,),
                )
                await db.commit()
            return Success(data=cursor.rowcount)
        except Exception as e:
            raise WebhookDatabaseError() from e

    # ── Update ────────────────────────────────────────────────────

    async def update_bot_info(self, bot_id: int, bot_info: str) -> Success[bool]:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "UPDATE webhook_info SET bot_info = ? WHERE bot_id = ?",
                    (bot_info, bot_id),
                )
                await db.commit()
                if cursor.rowcount == 0:
                    raise WebhookNotFoundError()
            return Success(data=True)
        except WebhookNotFoundError:
            raise
        except Exception as e:
            raise WebhookDatabaseError() from e

    # ── Lookup by webhook_id ───────────────────────────────────

    async def get_by_webhook_id(self, webhook_id: str) -> Success[WebhookInfo]:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT * FROM webhook_info WHERE bot_id = ?",
                    (webhook_id,),
                )
                row = await cursor.fetchone()
                if row is None:
                    raise WebhookNotFoundError()
                info = WebhookInfo(
                    webhook_id=row["bot_id"],
                    channel_id=row["channel_id"],
                    webhook_system_information=row["bot_info"],
                )
            return Success(data=info)
        except WebhookNotFoundError:
            raise
        except Exception as e:
            raise WebhookDatabaseError() from e

    # ── Convenience getter ────────────────────────────────────────

    async def get_bot_info(self, bot_id: int) -> Success[str | None]:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT bot_info FROM webhook_info WHERE bot_id = ?",
                    (bot_id,),
                )
                row = await cursor.fetchone()
                if row is None:
                    raise WebhookNotFoundError()
            return Success(data=row[0])
        except WebhookNotFoundError:
            raise
        except Exception as e:
            raise WebhookDatabaseError() from e