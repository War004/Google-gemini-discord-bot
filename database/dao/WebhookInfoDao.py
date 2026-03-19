import aiosqlite
import sqlite3
from pathlib import Path
from loader.Results import Success, Error
from database.domain.WebhookInfo import WebhookInfo


class WebhookInfoDao:

    def __init__(self, db_path: Path):
        self.db_path = db_path

    # ── Core methods ──────────────────────────────────────────────

    async def save(self, webhook_info: WebhookInfo) -> Success[WebhookInfo] | Error:
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
                return Error(
                    message="Channel entry doesn't exist.", 
                    solution="The solution is to add an API key first.",
                    exception=e
                )
            return Error(message="Failed to save webhook info due to integrity error", exception=e)
        except Exception as e:
            print(e)
            return Error(message="Failed to save webhook info", exception=e)

    async def delete(self, bot_id: int) -> Success[bool] | Error:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "DELETE FROM webhook_info WHERE bot_id = ?",
                    (bot_id,),
                )
                await db.commit()
                if cursor.rowcount == 0:
                    return Error(message="Webhook info not found", code=404)
            return Success(data=True)
        except Exception as e:
            return Error(message="Failed to delete webhook info", exception=e)

    async def get(self, bot_id: int) -> Success[WebhookInfo] | Error:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT * FROM webhook_info WHERE bot_id = ?",
                    (bot_id,),
                )
                row = await cursor.fetchone()
                if row is None:
                    return Error(message="Webhook info not found", code=404)
                info = WebhookInfo(
                    webhook_id=row["bot_id"],
                    channel_id=row["channel_id"],
                    webhook_system_information=row["bot_info"],
                )
            return Success(data=info)
        except Exception as e:
            return Error(message="Failed to get webhook info", exception=e)

    # ── Bulk / query methods ──────────────────────────────────────

    async def get_by_channel(self, channel_id: str) -> Success[list[WebhookInfo]] | Error:
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
            return Error(message="Failed to get webhooks by channel", exception=e)

    async def delete_by_channel(self, channel_id: str) -> Success[int] | Error:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "DELETE FROM webhook_info WHERE channel_id = ?",
                    (channel_id,),
                )
                await db.commit()
            return Success(data=cursor.rowcount)
        except Exception as e:
            return Error(message="Failed to delete webhooks by channel", exception=e)

    # ── Update ────────────────────────────────────────────────────

    async def update_bot_info(self, bot_id: int, bot_info: str) -> Success[bool] | Error:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "UPDATE webhook_info SET bot_info = ? WHERE bot_id = ?",
                    (bot_info, bot_id),
                )
                await db.commit()
                if cursor.rowcount == 0:
                    return Error(message="Webhook info not found", code=404)
            return Success(data=True)
        except Exception as e:
            return Error(message="Failed to update bot info", exception=e)
    # ── Lookup by webhook_id ───────────────────────────────────

    async def get_by_webhook_id(self, webhook_id: str) -> Success[WebhookInfo] | Error:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT * FROM webhook_info WHERE bot_id = ?",
                    (webhook_id,),
                )
                row = await cursor.fetchone()
                if row is None:
                    return Error(message="Webhook made by bot, but defination doesn't exist in db.", code=404, solution="Delete the webhook.")
                info = WebhookInfo(
                    webhook_id=row["bot_id"],
                    channel_id=row["channel_id"],
                    webhook_system_information=row["bot_info"],
                )
            return Success(data=info)
        except Exception as e:
            return Error(message="Failed to get webhook by webhook_id", exception=e)
    # ── Convenience getter ────────────────────────────────────────

    async def get_bot_info(self, bot_id: int) -> Success[str | None] | Error:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT bot_info FROM webhook_info WHERE bot_id = ?",
                    (bot_id,),
                )
                row = await cursor.fetchone()
                if row is None:
                    return Error(message="Webhook info not found", code=404)
            return Success(data=row[0])
        except Exception as e:
            return Error(message="Failed to get bot info", exception=e)
