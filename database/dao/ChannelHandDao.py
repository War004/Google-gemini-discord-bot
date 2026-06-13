import aiosqlite
from pathlib import Path
from src.loader.Results import Success
from database.domain.ChannelConfig import ChannelConfig
from database.exceptions.database_exception import ChannelConfigNotFoundError,InvalidColumnError,ChannelConfigDatabaseError


class ChannelHandDao:
    _UPDATABLE_COLUMNS = {"api_key", "model_name", "default_lan_code", "r18_enabled"}
    _GETTABLE_COLUMNS = {"api_key", "model_name", "default_lan_code", "r18_enabled"}

    def __init__(self, db_path: Path):
        self.db_path = db_path

    # ── Core methods ──────────────────────────────────────────────

    async def save(self, channel_config: ChannelConfig) -> Success[ChannelConfig]:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """INSERT OR REPLACE INTO channel_config
                       (channel_id, api_key, model_name, default_lan_code, r18_enabled)
                       VALUES (?, ?, ?, ?, ?)""",
                    (
                        channel_config.channel_id,
                        channel_config.api_key,
                        channel_config.model_name,
                        channel_config.default_lan_code,
                        channel_config.r18_enabled,
                    ),
                )
                await db.commit()
            return Success(data=channel_config)
        except Exception as e:
            raise ChannelConfigDatabaseError() from e

    async def delete(self, channel_id: str) -> Success[bool]:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("PRAGMA foreign_keys = ON;")
                cursor = await db.execute(
                    "DELETE FROM channel_config WHERE channel_id = ?",
                    (channel_id,),
                )
                await db.commit()
                if cursor.rowcount == 0:
                    raise ChannelConfigNotFoundError()
            return Success(data=True)
        except ChannelConfigNotFoundError:
            raise
        except Exception as e:
            raise ChannelConfigDatabaseError() from e

    async def get(self, channel_id: str) -> Success[ChannelConfig]:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT * FROM channel_config WHERE channel_id = ?",
                    (channel_id,),
                )
                row = await cursor.fetchone()
                if row is None:
                    raise ChannelConfigNotFoundError()
                config = ChannelConfig(
                    channel_id=row["channel_id"],
                    api_key=row["api_key"],
                    model_name=row["model_name"],
                    default_lan_code=row["default_lan_code"],
                    r18_enabled=bool(row["r18_enabled"]),
                )
            return Success(data=config)
        except ChannelConfigNotFoundError:
            raise
        except Exception as e:
            raise ChannelConfigDatabaseError() from e

    # ── Updates ───────────────────────────────────────────────────

    async def update_api_key(self, channel_id: str, api_key: str | None) -> Success[bool]:
        return await self._update_field(channel_id, "api_key", api_key)

    async def update_model_name(self, channel_id: str, model_name: str | None) -> Success[bool]:
        return await self._update_field(channel_id, "model_name", model_name)

    async def update_lan_code(self, channel_id: str, lan_code: str | None) -> Success[bool]:
        return await self._update_field(channel_id, "default_lan_code", lan_code)

    async def update_r18(self, channel_id: str, enabled: bool) -> Success[bool]:
        return await self._update_field(channel_id, "r18_enabled", enabled)

    # ── Convenience getters ───────────────────────────────────────

    async def get_api_key(self, channel_id: str) -> Success[str | None]:
        return await self._get_field(channel_id, "api_key")

    async def get_model_name(self, channel_id: str) -> Success[str | None]:
        return await self._get_field(channel_id, "model_name")

    async def get_lan_code(self, channel_id: str) -> Success[str | None]:
        return await self._get_field(channel_id, "default_lan_code")

    async def get_r18(self, channel_id: str) -> Success[bool]:
        result = await self._get_field(channel_id, "r18_enabled")
        return Success(data=bool(result.data))

    # ── Query methods ─────────────────────────────────────────────

    async def get_channels_with_api_key(self) -> Success[list[str]]:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT channel_id FROM channel_config WHERE api_key IS NOT NULL"
                )
                rows = await cursor.fetchall()
                channel_ids = [row[0] for row in rows]
            return Success(data=channel_ids)
        except Exception as e:
            raise ChannelConfigDatabaseError() from e

    async def get_channels_with_lan_code(self) -> Success[list[str]]:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT channel_id FROM channel_config WHERE default_lan_code IS NOT NULL"
                )
                rows = await cursor.fetchall()
                channel_ids = [row[0] for row in rows]
            return Success(data=channel_ids)
        except Exception as e:
            raise ChannelConfigDatabaseError() from e

    # ── Internal helpers ──────────────────────────────────────────

    async def _update_field(self, channel_id: str, column: str, value) -> Success[bool]:
        if column not in self._UPDATABLE_COLUMNS:
            raise InvalidColumnError(f"Invalid column: {column}")
        try:
            async with aiosqlite.connect(self.db_path) as db:
                query = f"""
                    INSERT INTO channel_config (channel_id, {column})
                    VALUES (?, ?)
                    ON CONFLICT(channel_id)
                    DO UPDATE SET {column} = excluded.{column}
                """
                await db.execute(query, (channel_id, value))
                await db.commit()
            return Success(data=True)
        except Exception as e:
            raise ChannelConfigDatabaseError() from e

    async def _get_field(self, channel_id: str, column: str) -> Success:
        if column not in self._GETTABLE_COLUMNS:
            raise InvalidColumnError(f"Invalid column: {column}")
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    f"SELECT {column} FROM channel_config WHERE channel_id = ?",
                    (channel_id,),
                )
                row = await cursor.fetchone()
                if row is None:
                    raise ChannelConfigNotFoundError()
            return Success(data=row[0])
        except ChannelConfigNotFoundError:
            raise
        except Exception as e:
            raise ChannelConfigDatabaseError() from e