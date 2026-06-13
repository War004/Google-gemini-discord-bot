from pathlib import Path
from src.loader.Results import Success, Error
from database.domain.Persona import Persona
from database.dao.PersonaDao import PersonaDao
from database.exceptions.database_exception import PersonaNotFoundError,PersonaDatabaseError
from src.translator.base_translator import BaseTranslator
from src.translator.lan_key import LangKey

class PersonaRepo:

    def __init__(self, db_path: Path, translation: BaseTranslator):
        self._dao = PersonaDao(db_path)
        self.translation = translation

    def _t(self, key: str, lan_code: str) -> str:
        return self.translation.get_translation_via_bypass_db(string_key=key, lan_code=lan_code)

    # ── Core ──────────────────────────────────────────────────────

    async def save(self, persona: Persona, lan_code: str = "en") -> Success[Persona] | Error:
        try:
            return await self._dao.save(persona)
        except PersonaDatabaseError as e:
            return Error(
                message=self._t(LangKey.PERSONA_DATABASE_ERROR, lan_code),
                exception=e,
            )

    async def delete(self, hash: str, lan_code: str = "en") -> Success[bool] | Error:
        try:
            return await self._dao.delete(hash)
        except PersonaNotFoundError as e:
            return Error(
                message=self._t(LangKey.PERSONA_NOT_FOUND, lan_code),
                exception=e,
            )
        except PersonaDatabaseError as e:
            return Error(
                message=self._t(LangKey.PERSONA_DATABASE_ERROR, lan_code),
                exception=e,
            )

    async def get(self, hash: str, lan_code: str = "en") -> Success[Persona] | Error:
        try:
            return await self._dao.get(hash)
        except PersonaNotFoundError as e:
            return Error(
                message=self._t(LangKey.PERSONA_NOT_FOUND, lan_code),
                exception=e,
            )
        except PersonaDatabaseError as e:
            return Error(
                message=self._t(LangKey.PERSONA_DATABASE_ERROR, lan_code),
                exception=e,
            )

    # ── Query ─────────────────────────────────────────────────────

    async def get_all(self, lan_code: str = "en") -> Success[list[Persona]] | Error:
        try:
            return await self._dao.get_all()
        except PersonaDatabaseError as e:
            return Error(
                message=self._t(LangKey.PERSONA_DATABASE_ERROR, lan_code),
                exception=e,
            )

    async def exists(self, hash: str, lan_code: str = "en") -> Success[bool] | Error:
        try:
            return await self._dao.exists(hash)
        except PersonaDatabaseError as e:
            return Error(
                message=self._t(LangKey.PERSONA_DATABASE_ERROR, lan_code),
                exception=e,
            )