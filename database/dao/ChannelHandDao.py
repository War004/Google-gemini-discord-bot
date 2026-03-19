import aiosqlite
from pathlib import Path
from loader.Results import Success, Error
from database.domain.ChannelConfig import ChannelConfig


class ChannelHandDao:
    _UPDATABLE_COLUMNS = {"api_key", "model_name", "default_lan_code", "r18_enabled"}
    _GETTABLE_COLUMNS = {"api_key", "model_name", "r18_enabled"}

    def __init__(self, db_path: Path):
        self.db_path = db_path

    # ── Core methods ──────────────────────────────────────────────

    async def save(self, channel_config: ChannelConfig) -> Success[ChannelConfig] | Error:
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
            return Error(message="Failed to save channel config", exception=e)

    async def delete(self, channel_id: str) -> Success[bool] | Error:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("PRAGMA foreign_keys = ON;")
                cursor = await db.execute(
                    "DELETE FROM channel_config WHERE channel_id = ?",
                    (channel_id,),
                )
                await db.commit()
                if cursor.rowcount == 0:
                    return Error(message="Channel config not found", code=404)
            return Success(data=True)
        except Exception as e:
            return Error(message="Failed to delete channel config", exception=e)

    async def get(self, channel_id: str) -> Success[ChannelConfig] | Error:
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(
                    "SELECT * FROM channel_config WHERE channel_id = ?",
                    (channel_id,),
                )
                row = await cursor.fetchone()
                if row is None:
                    return Error(message="Channel config not found", code=404)
                config = ChannelConfig(
                    channel_id=row["channel_id"],
                    api_key=row["api_key"],
                    model_name=row["model_name"],
                    default_lan_code=row["default_lan_code"],
                    r18_enabled=bool(row["r18_enabled"]),
                    )
                
            return Success(data=config)
        except Exception as e:
            return Error(message="Failed to get channel config. Please set the api", exception=e)

    # ── Updates ───────────────────────────────────────────────────

    async def update_api_key(self, channel_id: str, api_key: str | None) -> Success[bool] | Error:
        return await self._update_field(channel_id, "api_key", api_key)

    async def update_model_name(self, channel_id: str, model_name: str | None) -> Success[bool] | Error:
        return await self._update_field(channel_id, "model_name", model_name)

    async def update_lan_code(self, channel_id: str, lan_code: str | None) -> Success[bool] | Error:
        return await self._update_field(channel_id, "default_lan_code", lan_code)

    async def update_r18(self, channel_id: str, enabled: bool) -> Success[bool] | Error:
        return await self._update_field(channel_id, "r18_enabled", enabled)

    # ── Convenience getters ───────────────────────────────────────

    async def get_api_key(self, channel_id: str) -> Success[str | None] | Error:
        return await self._get_field(channel_id, "api_key")

    async def get_model_name(self, channel_id: str) -> Success[str | None] | Error:
        return await self._get_field(channel_id, "model_name")

    async def get_r18(self, channel_id: str) -> Success[bool] | Error:
        result = await self._get_field(channel_id, "r18_enabled")
        if isinstance(result, Success):
            return Success(data=bool(result.data))
        return result

    # ── Internal helpers ──────────────────────────────────────────

    async def _update_field(self, channel_id: str, column: str, value) -> Success[bool] | Error:
        if column not in self._UPDATABLE_COLUMNS:
            return Error(message=f"Invalid column: {column}")
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # The Upsert Query: Insert if new, update if exists
                query = f"""
                    INSERT INTO channel_config (channel_id, {column}) 
                    VALUES (?, ?) 
                    ON CONFLICT(channel_id) 
                    DO UPDATE SET {column} = excluded.{column}
                """
                await db.execute(query, (channel_id, value))
                await db.commit()
                
            # Automatically successful if no exception is thrown
            return Success(data=True)
            
        except Exception as e:
            return Error(message=f"Failed to update {column}", exception=e)

    async def _get_field(self, channel_id: str, column: str) -> Success | Error:
        if column not in self._GETTABLE_COLUMNS:
            return Error(message=f"Invalid column: {column}")
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    f"SELECT {column} FROM channel_config WHERE channel_id = ?",
                    (channel_id,),
                )
                row = await cursor.fetchone()
                if row is None:
                    return Error(message="Channel config not found", code=404)
            return Success(data=row[0])
        except Exception as e:
            return Error(message=f"Failed to get {column}", exception=e)
