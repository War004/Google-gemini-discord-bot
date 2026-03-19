from pathlib import Path
from loader.Results import Success, Error
from database.domain.WebhookInfo import WebhookInfo
from database.dao.WebhookInfoDao import WebhookInfoDao


class WebhookInfoRepo:

    def __init__(self, db_path: Path):
        self._dao = WebhookInfoDao(db_path)

    # ── Core ──────────────────────────────────────────────────────

    async def save(self, webhook_info: WebhookInfo) -> Success[WebhookInfo] | Error:
        return await self._dao.save(webhook_info)

    async def delete(self, bot_id: int) -> Success[bool] | Error:
        return await self._dao.delete(bot_id)

    async def get(self, bot_id: int) -> Success[WebhookInfo] | Error:
        return await self._dao.get(bot_id)

    # ── Bulk / query ──────────────────────────────────────────────

    async def get_by_channel(self, channel_id: str) -> Success[list[WebhookInfo]] | Error:
        return await self._dao.get_by_channel(channel_id)

    async def delete_by_channel(self, channel_id: str) -> Success[int] | Error:
        return await self._dao.delete_by_channel(channel_id)

    # ── Update ────────────────────────────────────────────────────

    async def update_bot_info(self, bot_id: int, bot_info: str) -> Success[bool] | Error:
        return await self._dao.update_bot_info(bot_id, bot_info)
    # ── Lookup by webhook_id ─────────────────────────────────

    async def get_by_webhook_id(self, webhook_id: str) -> Success[WebhookInfo] | Error:
        return await self._dao.get_by_webhook_id(webhook_id)
    # ── Convenience getter ────────────────────────────────────────

    async def get_bot_info(self, bot_id: int) -> Success[str | None] | Error:
        return await self._dao.get_bot_info(bot_id)
