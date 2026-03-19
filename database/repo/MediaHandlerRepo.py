from pathlib import Path
from loader.Results import Success, Error
from database.domain.MediaHandler import MediaHandler
from database.dao.MediaHandlerDao import MediaHandlerDao


class MediaHandlerRepo:

    def __init__(self, db_path: Path):
        self._dao = MediaHandlerDao(db_path)

    # ── Core ──────────────────────────────────────────────────────

    async def save(self, media: MediaHandler) -> Success[MediaHandler] | Error:
        return await self._dao.save(media)

    async def delete(self, chat_id: str) -> Success[bool] | Error:
        return await self._dao.delete(chat_id)

    async def get(self, chat_id: str) -> Success[MediaHandler] | Error:
        return await self._dao.get(chat_id)

    # ── Bulk / query ──────────────────────────────────────────────

    async def get_by_channel(self, channel_id: str) -> Success[list[MediaHandler]] | Error:
        return await self._dao.get_by_channel(channel_id)

    async def delete_by_channel(self, channel_id: str) -> Success[int] | Error:
        return await self._dao.delete_by_channel(channel_id)

    # ── Expiry ────────────────────────────────────────────────────

    async def get_expired(self, before_timestamp: int) -> Success[list[MediaHandler]] | Error:
        return await self._dao.get_expired(before_timestamp)

    async def get_expired_by_channel(self, channel_id: str, before_timestamp: int) -> Success[list[MediaHandler]] | Error:
        return await self._dao.get_expired_by_channel(channel_id, before_timestamp)

    async def delete_expired(self, before_timestamp: int) -> Success[int] | Error:
        return await self._dao.delete_expired(before_timestamp)
