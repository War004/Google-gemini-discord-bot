from pathlib import Path
from src.loader.Results import Success, Error
from database.domain.MediaHandler import MediaHandler
from database.dao.MediaHandlerDao import MediaHandlerDao
from database.exceptions.database_exception import MediaHandlerNotFoundError, ChannelNotFoundError,MediaHandlerIntegrityError,MediaHandlerDatabaseError
from src.translator.base_translator import BaseTranslator
from src.translator.lan_key import LangKey

class MediaHandlerRepo:

    def __init__(self, db_path: Path, translation: BaseTranslator):
        self._dao = MediaHandlerDao(db_path)
        self.translation = translation

    def _t(self, key: str, lan_code: str) -> str:
        return self.translation.get_translation_via_bypass_db(string_key=key, lan_code=lan_code)

    # ── Core ──────────────────────────────────────────────────────

    async def save(self, media: MediaHandler, lan_code: str = "en") -> Success[MediaHandler] | Error:
        try:
            return await self._dao.save(media)
        except ChannelNotFoundError as e:
            return Error(
                message=self._t(LangKey.MEDIA_HANDLER_CHANNEL_NOT_FOUND, lan_code),
                solution=self._t(LangKey.MEDIA_HANDLER_ADD_API_KEY, lan_code),
                exception=e,
            )
        except MediaHandlerIntegrityError as e:
            return Error(
                message=self._t(LangKey.MEDIA_HANDLER_INTEGRITY_ERROR, lan_code),
                exception=e,
            )
        except MediaHandlerDatabaseError as e:
            return Error(
                message=self._t(LangKey.MEDIA_HANDLER_DATABASE_ERROR, lan_code),
                exception=e,
            )

    async def delete(self, chat_id: str, lan_code: str = "en") -> Success[bool] | Error:
        try:
            return await self._dao.delete(chat_id)
        except MediaHandlerNotFoundError as e:
            return Error(
                message=self._t(LangKey.MEDIA_HANDLER_NOT_FOUND, lan_code),
                exception=e,
            )
        except MediaHandlerDatabaseError as e:
            return Error(
                message=self._t(LangKey.MEDIA_HANDLER_DATABASE_ERROR, lan_code),
                exception=e,
            )

    async def get(self, chat_id: str, lan_code: str = "en") -> Success[MediaHandler] | Error:
        try:
            return await self._dao.get(chat_id)
        except MediaHandlerNotFoundError as e:
            return Error(
                message=self._t(LangKey.MEDIA_HANDLER_NOT_FOUND, lan_code),
                exception=e,
            )
        except MediaHandlerDatabaseError as e:
            return Error(
                message=self._t(LangKey.MEDIA_HANDLER_DATABASE_ERROR, lan_code),
                exception=e,
            )

    # ── Bulk / query ──────────────────────────────────────────────

    async def get_by_channel(self, channel_id: str, lan_code: str = "en") -> Success[list[MediaHandler]] | Error:
        try:
            return await self._dao.get_by_channel(channel_id)
        except MediaHandlerDatabaseError as e:
            return Error(
                message=self._t(LangKey.MEDIA_HANDLER_DATABASE_ERROR, lan_code),
                exception=e,
            )

    async def delete_by_channel(self, channel_id: str, lan_code: str = "en") -> Success[int] | Error:
        try:
            return await self._dao.delete_by_channel(channel_id)
        except MediaHandlerDatabaseError as e:
            return Error(
                message=self._t(LangKey.MEDIA_HANDLER_DATABASE_ERROR, lan_code),
                exception=e,
            )

    # ── Expiry ────────────────────────────────────────────────────

    async def get_expired(self, before_timestamp: int, lan_code: str = "en") -> Success[list[MediaHandler]] | Error:
        try:
            return await self._dao.get_expired(before_timestamp)
        except MediaHandlerDatabaseError as e:
            return Error(
                message=self._t(LangKey.MEDIA_HANDLER_DATABASE_ERROR, lan_code),
                exception=e,
            )

    async def get_expired_by_chat_id(self, chat_id: str, before_timestamp: int, lan_code: str = "en") -> Success[list[MediaHandler]] | Error:
        try:
            return await self._dao.get_expired_by_chat_id(chat_id, before_timestamp)
        except MediaHandlerDatabaseError as e:
            return Error(
                message=self._t(LangKey.MEDIA_HANDLER_DATABASE_ERROR, lan_code),
                exception=e,
            )

    async def delete_expired(self, before_timestamp: int, lan_code: str = "en") -> Success[int] | Error:
        try:
            return await self._dao.delete_expired(before_timestamp)
        except MediaHandlerDatabaseError as e:
            return Error(
                message=self._t(LangKey.MEDIA_HANDLER_DATABASE_ERROR, lan_code),
                exception=e,
            )