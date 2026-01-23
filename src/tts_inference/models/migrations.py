"""Database migration system for schema versioning."""

import aiosqlite
from pathlib import Path
from typing import List, Callable, Awaitable
import logging

logger = logging.getLogger(__name__)


class Migration:
    """Represents a single database migration."""
    
    def __init__(self, version: int, name: str, up: Callable[[aiosqlite.Connection], Awaitable[None]]):
        """Initialize migration.
        
        Args:
            version: Migration version number (sequential)
            name: Human-readable migration name
            up: Async function to apply migration (receives db connection)
        """
        self.version = version
        self.name = name
        self.up = up
    
    async def apply(self, db: aiosqlite.Connection):
        """Apply this migration to the database.
        
        Args:
            db: Database connection
        """
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
        """Initialize migration manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.migrations: List[Migration] = []
    
    def register(self, version: int, name: str):
        """Decorator to register a migration function.
        
        Args:
            version: Migration version number
            name: Human-readable migration name
            
        Example:
            @migrator.register(1, "add_emotional_tables")
            async def migrate(db):
                await db.execute("CREATE TABLE ...")
        """
        def decorator(func: Callable[[aiosqlite.Connection], Awaitable[None]]):
            self.migrations.append(Migration(version, name, func))
            return func
        return decorator
    
    async def initialize_migrations_table(self):
        """Create the schema_migrations table if it doesn't exist."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()
            logger.info("Migration tracking table initialized")
    
    async def get_current_version(self) -> int:
        """Get the current schema version.
        
        Returns:
            Current version number (0 if no migrations applied)
        """
        async with aiosqlite.connect(self.db_path) as db:
            # Check if migrations table exists
            async with db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
            ) as cursor:
                if not await cursor.fetchone():
                    return 0
            
            # Get highest version number
            async with db.execute(
                "SELECT MAX(version) FROM schema_migrations"
            ) as cursor:
                result = await cursor.fetchone()
                return result[0] if result[0] is not None else 0
    
    async def run_migrations(self):
        """Run all pending migrations in order."""
        await self.initialize_migrations_table()
        current_version = await self.get_current_version()
        
        # Sort migrations by version
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
    
    async def get_migration_history(self) -> List[dict]:
        """Get the history of applied migrations.
        
        Returns:
            List of migration records
        """
        await self.initialize_migrations_table()
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM schema_migrations ORDER BY version"
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
