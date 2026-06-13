from pathlib import Path
from src.loader.Results import Success, Error
from database.domain.WebhookInfo import WebhookInfo
from database.dao.WebhookInfoDao import WebhookInfoDao
from database.exceptions.database_exception import ChannelNotFoundError,WebhookNotFoundError,WebhookIntegrityError,WebhookDatabaseError
from src.translator.base_translator import BaseTranslator
from src.translator.lan_key import LangKey

class WebhookInfoRepo:

    def __init__(self, db_path: Path, translation: BaseTranslator):
        self._dao = WebhookInfoDao(db_path)
        self.translation = translation

    def _t(self, key: str, lan_code: str) -> str:
        return self.translation.get_translation_via_bypass_db(string_key=key, lan_code=lan_code)

    # ── Core ──────────────────────────────────────────────────────

    async def save(self, webhook_info: WebhookInfo, lan_code: str = "en") -> Success[WebhookInfo] | Error:
        try:
            return await self._dao.save(webhook_info)
        except ChannelNotFoundError as e:
            return Error(
                message=self._t(LangKey.WEBHOOK_CHANNEL_NOT_FOUND, lan_code),
                solution=self._t(LangKey.WEBHOOK_ADD_API_KEY, lan_code),
                exception=e,
            )
        except WebhookIntegrityError as e:
            return Error(
                message=self._t(LangKey.WEBHOOK_INTEGRITY_ERROR, lan_code),
                exception=e,
            )
        except WebhookDatabaseError as e:
            return Error(
                message=self._t(LangKey.WEBHOOK_DATABASE_ERROR, lan_code),
                exception=e,
            )

    async def delete(self, bot_id: int, lan_code: str = "en") -> Success[bool] | Error:
        try:
            return await self._dao.delete(bot_id)
        except WebhookNotFoundError as e:
            return Error(
                message=self._t(LangKey.WEBHOOK_NOT_FOUND, lan_code),
                exception=e,
            )
        except WebhookDatabaseError as e:
            return Error(
                message=self._t(LangKey.WEBHOOK_DATABASE_ERROR, lan_code),
                exception=e,
            )

    async def get(self, bot_id: int, lan_code: str = "en") -> Success[WebhookInfo] | Error:
        try:
            return await self._dao.get(bot_id)
        except WebhookNotFoundError as e:
            return Error(
                message=self._t(LangKey.WEBHOOK_NOT_FOUND, lan_code),
                exception=e,
            )
        except WebhookDatabaseError as e:
            return Error(
                message=self._t(LangKey.WEBHOOK_DATABASE_ERROR, lan_code),
                exception=e,
            )

    # ── Bulk / query ──────────────────────────────────────────────

    async def get_by_channel(self, channel_id: str, lan_code: str = "en") -> Success[list[WebhookInfo]] | Error:
        try:
            return await self._dao.get_by_channel(channel_id)
        except WebhookDatabaseError as e:
            return Error(
                message=self._t(LangKey.WEBHOOK_DATABASE_ERROR, lan_code),
                exception=e,
            )

    async def delete_by_channel(self, channel_id: str, lan_code: str = "en") -> Success[int] | Error:
        try:
            return await self._dao.delete_by_channel(channel_id)
        except WebhookDatabaseError as e:
            return Error(
                message=self._t(LangKey.WEBHOOK_DATABASE_ERROR, lan_code),
                exception=e,
            )

    # ── Update ────────────────────────────────────────────────────

    async def update_bot_info(self, bot_id: int, bot_info: str, lan_code: str = "en") -> Success[bool] | Error:
        try:
            return await self._dao.update_bot_info(bot_id, bot_info)
        except WebhookNotFoundError as e:
            return Error(
                message=self._t(LangKey.WEBHOOK_NOT_FOUND, lan_code),
                exception=e,
            )
        except WebhookDatabaseError as e:
            return Error(
                message=self._t(LangKey.WEBHOOK_DATABASE_ERROR, lan_code),
                exception=e,
            )

    # ── Lookup by webhook_id ─────────────────────────────────

    async def get_by_webhook_id(self, webhook_id: str, lan_code: str = "en") -> Success[WebhookInfo] | Error:
        try:
            return await self._dao.get_by_webhook_id(webhook_id)
        except WebhookNotFoundError as e:
            return Error(
                message=self._t(LangKey.WEBHOOK_NOT_FOUND, lan_code),
                exception=e,
            )
        except WebhookDatabaseError as e:
            return Error(
                message=self._t(LangKey.WEBHOOK_DATABASE_ERROR, lan_code),
                exception=e,
            )

    # ── Convenience getter ────────────────────────────────────────

    async def get_bot_info(self, bot_id: int, lan_code: str = "en") -> Success[str | None] | Error:
        try:
            return await self._dao.get_bot_info(bot_id)
        except WebhookNotFoundError as e:
            return Error(
                message=self._t(LangKey.WEBHOOK_NOT_FOUND, lan_code),
                exception=e,
            )
        except WebhookDatabaseError as e:
            return Error(
                message=self._t(LangKey.WEBHOOK_DATABASE_ERROR, lan_code),
                exception=e,
            )