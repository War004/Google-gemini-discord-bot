from pathlib import Path
from loader.Results import Success, Error
from database.domain.ChannelConfig import ChannelConfig
from database.dao.ChannelHandDao import ChannelHandDao


class ChannelConfigRepo:

    def __init__(self, db_path: Path):
        self._dao = ChannelHandDao(db_path)

    # ── Core ──────────────────────────────────────────────────────

    async def save(self, channel_config: ChannelConfig) -> Success[ChannelConfig] | Error:
        return await self._dao.save(channel_config)

    async def delete(self, channel_id: str) -> Success[bool] | Error:
        return await self._dao.delete(channel_id)

    async def get(self, channel_id: str) -> Success[ChannelConfig] | Error:
        return await self._dao.get(channel_id)

    # ── Updates ───────────────────────────────────────────────────

    async def update_api_key(self, channel_id: str, api_key: str | None) -> Success[bool] | Error:
        return await self._dao.update_api_key(channel_id, api_key)

    async def update_model_name(self, channel_id: str, model_name: str | None) -> Success[bool] | Error:
        return await self._dao.update_model_name(channel_id, model_name)

    async def update_lan_code(self, channel_id: str, lan_code: str | None) -> Success[bool] | Error:
        return await self._dao.update_lan_code(channel_id, lan_code)

    async def update_r18(self, channel_id: str, enabled: bool) -> Success[bool] | Error:
        return await self._dao.update_r18(channel_id, enabled)

    # ── Convenience getters ───────────────────────────────────────

    async def get_api_key(self, channel_id: str) -> Success[str | None] | Error:
        return await self._dao.get_api_key(channel_id)

    async def get_model_name(self, channel_id: str) -> Success[str | None] | Error:
        return await self._dao.get_model_name(channel_id)

    async def get_r18(self, channel_id: str) -> Success[bool] | Error:
        return await self._dao.get_r18(channel_id)
