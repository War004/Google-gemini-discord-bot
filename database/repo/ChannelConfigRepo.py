from pathlib import Path
from src.loader.Results import Success, Error
from database.domain.ChannelConfig import ChannelConfig
from database.dao.ChannelHandDao import ChannelHandDao
from database.exceptions.database_exception import ChannelConfigNotFoundError,InvalidColumnError,ChannelConfigDatabaseError
from src.BloomFilter import BloomFilter
from src.translator.base_translator import BaseTranslator
from src.translator.lan_key import LangKey


class ChannelConfigRepo:

    def __init__(self, db_path: Path, api_bloom: BloomFilter, lan_bloom: BloomFilter, translation: BaseTranslator):
        self._dao = ChannelHandDao(db_path)
        self.__api_bloom__ = api_bloom
        self.__lan_bloom__ = lan_bloom
        self.translation = translation

    def _t(self, key: str, lan_code: str) -> str:
        return self.translation.get_translation_via_bypass_db(string_key=key, lan_code=lan_code)

    # ── Core ──────────────────────────────────────────────────────

    async def save(self, channel_config: ChannelConfig, lan_code: str = "en") -> Success[ChannelConfig] | Error:
        try:
            return await self._dao.save(channel_config)
        except ChannelConfigDatabaseError as e:
            return Error(
                message=self._t(LangKey.CHANNEL_CONFIG_DATABASE_ERROR, lan_code),
                exception=e,
            )

    async def delete(self, channel_id: str, lan_code: str = "en") -> Success[bool] | Error:
        try:
            return await self._dao.delete(channel_id)
        except ChannelConfigNotFoundError as e:
            return Error(
                message=self._t(LangKey.CHANNEL_CONFIG_NOT_FOUND, lan_code),
                exception=e,
            )
        except ChannelConfigDatabaseError as e:
            return Error(
                message=self._t(LangKey.CHANNEL_CONFIG_DATABASE_ERROR, lan_code),
                exception=e,
            )

    async def get(self, channel_id: str, lan_code: str = "en") -> Success[ChannelConfig] | Error:
        try:
            return await self._dao.get(channel_id)
        except ChannelConfigNotFoundError as e:
            return Error(
                message=self._t(LangKey.CHANNEL_CONFIG_NOT_FOUND, lan_code),
                exception=e,
            )
        except ChannelConfigDatabaseError as e:
            return Error(
                message=self._t(LangKey.CHANNEL_CONFIG_DATABASE_ERROR, lan_code),
                exception=e,
            )

    # ── Updates ───────────────────────────────────────────────────

    async def update_api_key(self, channel_id: str, api_key: str | None, lan_code: str = "en") -> Success[bool] | Error:
        try:
            result = await self._dao.update_api_key(channel_id, api_key)
            self.__api_bloom__.add(channel_id)
            return result
        except InvalidColumnError as e:
            return Error(
                message=self._t(LangKey.CHANNEL_CONFIG_INVALID_COLUMN, lan_code),
                exception=e,
            )
        except ChannelConfigDatabaseError as e:
            return Error(
                message=self._t(LangKey.CHANNEL_CONFIG_DATABASE_ERROR, lan_code),
                exception=e,
            )

    async def update_model_name(self, channel_id: str, model_name: str | None, lan_code: str = "en") -> Success[bool] | Error:
        try:
            return await self._dao.update_model_name(channel_id, model_name)
        except InvalidColumnError as e:
            return Error(
                message=self._t(LangKey.CHANNEL_CONFIG_INVALID_COLUMN, lan_code),
                exception=e,
            )
        except ChannelConfigDatabaseError as e:
            return Error(
                message=self._t(LangKey.CHANNEL_CONFIG_DATABASE_ERROR, lan_code),
                exception=e,
            )

    async def update_lan_code(self, channel_id: str, default_lan_code: str | None, lan_code: str = "en") -> Success[bool] | Error:
        # NOTE: default_lan_code = value to store; lan_code = request language for translation
        try:
            result = await self._dao.update_lan_code(channel_id, default_lan_code)
            self.__lan_bloom__.add(channel_id)
            return result
        except InvalidColumnError as e:
            return Error(
                message=self._t(LangKey.CHANNEL_CONFIG_INVALID_COLUMN, lan_code),
                exception=e,
            )
        except ChannelConfigDatabaseError as e:
            return Error(
                message=self._t(LangKey.CHANNEL_CONFIG_DATABASE_ERROR, lan_code),
                exception=e,
            )

    async def update_r18(self, channel_id: str, enabled: bool, lan_code: str = "en") -> Success[bool] | Error:
        try:
            return await self._dao.update_r18(channel_id, enabled)
        except InvalidColumnError as e:
            return Error(
                message=self._t(LangKey.CHANNEL_CONFIG_INVALID_COLUMN, lan_code),
                exception=e,
            )
        except ChannelConfigDatabaseError as e:
            return Error(
                message=self._t(LangKey.CHANNEL_CONFIG_DATABASE_ERROR, lan_code),
                exception=e,
            )

    # ── Convenience getters ───────────────────────────────────────

    async def get_api_key(self, channel_id: str, lan_code: str = "en") -> Success[str | None] | Error:
        try:
            return await self._dao.get_api_key(channel_id)
        except ChannelConfigNotFoundError as e:
            return Error(
                message=self._t(LangKey.CHANNEL_CONFIG_NOT_FOUND, lan_code),
                exception=e,
            )
        except InvalidColumnError as e:
            return Error(
                message=self._t(LangKey.CHANNEL_CONFIG_INVALID_COLUMN, lan_code),
                exception=e,
            )
        except ChannelConfigDatabaseError as e:
            return Error(
                message=self._t(LangKey.CHANNEL_CONFIG_DATABASE_ERROR, lan_code),
                exception=e,
            )

    async def get_model_name(self, channel_id: str, lan_code: str = "en") -> Success[str | None] | Error:
        try:
            return await self._dao.get_model_name(channel_id)
        except ChannelConfigNotFoundError as e:
            return Error(
                message=self._t(LangKey.CHANNEL_CONFIG_NOT_FOUND, lan_code),
                exception=e,
            )
        except InvalidColumnError as e:
            return Error(
                message=self._t(LangKey.CHANNEL_CONFIG_INVALID_COLUMN, lan_code),
                exception=e,
            )
        except ChannelConfigDatabaseError as e:
            return Error(
                message=self._t(LangKey.CHANNEL_CONFIG_DATABASE_ERROR, lan_code),
                exception=e,
            )

    async def get_lan_code(self, channel_id: str, lan_code: str = "en") -> Success[str | None] | Error:
        try:
            return await self._dao.get_lan_code(channel_id)
        except ChannelConfigNotFoundError as e:
            return Error(
                message=self._t(LangKey.CHANNEL_CONFIG_NOT_FOUND, lan_code),
                exception=e,
            )
        except InvalidColumnError as e:
            return Error(
                message=self._t(LangKey.CHANNEL_CONFIG_INVALID_COLUMN, lan_code),
                exception=e,
            )
        except ChannelConfigDatabaseError as e:
            return Error(
                message=self._t(LangKey.CHANNEL_CONFIG_DATABASE_ERROR, lan_code),
                exception=e,
            )

    async def get_r18(self, channel_id: str, lan_code: str = "en") -> Success[bool] | Error:
        try:
            return await self._dao.get_r18(channel_id)
        except ChannelConfigNotFoundError as e:
            return Error(
                message=self._t(LangKey.CHANNEL_CONFIG_NOT_FOUND, lan_code),
                exception=e,
            )
        except InvalidColumnError as e:
            return Error(
                message=self._t(LangKey.CHANNEL_CONFIG_INVALID_COLUMN, lan_code),
                exception=e,
            )
        except ChannelConfigDatabaseError as e:
            return Error(
                message=self._t(LangKey.CHANNEL_CONFIG_DATABASE_ERROR, lan_code),
                exception=e,
            )

    # ── Query methods ─────────────────────────────────────────────

    async def get_channels_with_api_key(self, lan_code: str = "en") -> Success[list[str]] | Error:
        try:
            return await self._dao.get_channels_with_api_key()
        except ChannelConfigDatabaseError as e:
            return Error(
                message=self._t(LangKey.CHANNEL_CONFIG_DATABASE_ERROR, lan_code),
                exception=e,
            )

    async def get_channels_with_lan_code(self, lan_code: str = "en") -> Success[list[str]] | Error:
        try:
            return await self._dao.get_channels_with_lan_code()
        except ChannelConfigDatabaseError as e:
            return Error(
                message=self._t(LangKey.CHANNEL_CONFIG_DATABASE_ERROR, lan_code),
                exception=e,
            )