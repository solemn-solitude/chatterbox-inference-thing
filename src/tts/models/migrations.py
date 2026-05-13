"""Database migration system for schema versioning."""

import asyncio
import aiosqlite
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class Migration:
    """Represents a single database migration."""

    def __init__(self, version: int, name: str, up):
        self.version = version
        self.name = name
        self.up = up

    async def apply(self, db: aiosqlite.Connection):
        logger.info(f"Applying migration {self.version}: {self.name}")
        await self.up(db)
        await db.execute(
            "INSERT INTO schema_migrations (version, name) VALUES (?, ?)",
            (self.version, self.name)
        )
        await db.commit()
        logger.info(f"Migration {self.version} applied successfully")


class MigrationManager:
    """Manages database schema migrations."""

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.migrations: list[Migration] = []

    def register(self, version: int, name: str):
        def decorator(func):
            self.migrations.append(Migration(version, name, func))
            return func
        return decorator

    async def initialize_migrations_table(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()

    async def get_current_version(self) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
            ) as cursor:
                if not await cursor.fetchone():
                    return 0

            async with db.execute("SELECT MAX(version) FROM schema_migrations") as cursor:
                result = await cursor.fetchone()
                return result[0] if result[0] is not None else 0

    async def run_migrations(self):
        await self.initialize_migrations_table()
        current_version = await self.get_current_version()

        pending = sorted(
            [m for m in self.migrations if m.version > current_version],
            key=lambda m: m.version
        )

        if not pending:
            logger.info(f"Database is up to date (version {current_version})")
            return

        logger.info(f"Running {len(pending)} pending migrations from version {current_version}")

        async with aiosqlite.connect(self.db_path) as db:
            for migration in pending:
                await migration.apply(db)

        new_version = await self.get_current_version()
        logger.info(f"All migrations complete. Database version: {new_version}")

    async def get_migration_history(self) -> list[dict]:
        await self.initialize_migrations_table()

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM schema_migrations ORDER BY version"
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]


class SyncMigrationManager:
    """Synchronous wrapper around MigrationManager."""

    def __init__(self, db_path: Path):
        self._manager = MigrationManager(db_path)

    def run_migrations(self):
        asyncio.run(self._manager.run_migrations())

    def get_current_version(self) -> int:
        return asyncio.run(self._manager.get_current_version())

    def get_migration_history(self) -> list[dict]:
        return asyncio.run(self._manager.get_migration_history())


def get_migrator(db_path: Path) -> SyncMigrationManager:
    return SyncMigrationManager(db_path)
