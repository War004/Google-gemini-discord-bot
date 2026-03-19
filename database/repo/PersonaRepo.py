from pathlib import Path
from loader.Results import Success, Error
from database.domain.Persona import Persona
from database.dao.PersonaDao import PersonaDao


class PersonaRepo:

    def __init__(self, db_path: Path):
        self._dao = PersonaDao(db_path)

    # ── Core ──────────────────────────────────────────────────────

    async def save(self, persona: Persona) -> Success[Persona] | Error:
        return await self._dao.save(persona)

    async def delete(self, hash: str) -> Success[bool] | Error:
        return await self._dao.delete(hash)

    async def get(self, hash: str) -> Success[Persona] | Error:
        return await self._dao.get(hash)

    # ── Query ─────────────────────────────────────────────────────

    async def get_all(self) -> Success[list[Persona]] | Error:
        return await self._dao.get_all()

    async def exists(self, hash: str) -> Success[bool] | Error:
        return await self._dao.exists(hash)
