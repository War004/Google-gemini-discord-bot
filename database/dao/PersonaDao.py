import aiosqlite
from pathlib import Path
from loader.Results import Success, Error
from database.domain.Persona import Persona


class PersonaDao:

    def __init__(self, db_path: Path):
        self.db_path = db_path

    # ── Core methods ──────────────────────────────────────────────

    async def save(self, persona: Persona) -> Success[Persona] | Error:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """INSERT OR REPLACE INTO persona (hash, information)
                       VALUES (?, ?)""",
                    (persona.hash, persona.information),
                )
                await db.commit()
            return Success(data=persona)
        except Exception as e:
            return Error(message="Failed to save persona", exception=e)

    async def delete(self, hash: str) -> Success[bool] | Error:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "DELETE FROM persona WHERE hash = ?",
                    (hash,),
                )
                await db.commit()
                if cursor.rowcount == 0:
                    return Error(message="Persona not found", code=404)
            return Success(data=True)
        except Exception as e:
            return Error(message="Failed to delete persona", exception=e)

    async def get(self, hash: str) -> Success[Persona] | Error:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT * FROM persona WHERE hash = ?",
                    (hash,),
                )
                row = await cursor.fetchone()
                if row is None:
                    return Error(message="Persona not found", code=404)
                persona = Persona(
                    hash=row["hash"],
                    information=row["information"],
                )
            return Success(data=persona)
        except Exception as e:
            return Error(message="Failed to get persona", exception=e)

    async def get_all(self) -> Success[list[Persona]] | Error:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("SELECT * FROM persona")
                rows = await cursor.fetchall()
                personas = [
                    Persona(hash=row["hash"], information=row["information"])
                    for row in rows
                ]
            return Success(data=personas)
        except Exception as e:
            return Error(message="Failed to get all personas", exception=e)

    async def exists(self, hash: str) -> Success[bool] | Error:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT 1 FROM persona WHERE hash = ?",
                    (hash,),
                )
                row = await cursor.fetchone()
            return Success(data=row is not None)
        except Exception as e:
            return Error(message="Failed to check persona existence", exception=e)
