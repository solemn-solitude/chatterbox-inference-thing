"""Database management service - handles migrations and status."""

import logging
from pathlib import Path

from ..models.migrations import get_migrator
from ..utils.config import CONFIG
from ..models.service_dataclasses import MigrationStatus, MigrationRecord

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service for database operations."""

    def __init__(self, db_path: Path | None = None):
        """Initialize database service.

        Args:
            db_path: Path to database (defaults to CONFIG.database_path)
        """
        self.db_path = db_path or CONFIG.database_path

    def run_migrations(self) -> None:
        """Run all pending database migrations."""
        logger.info(f"Running migrations on {self.db_path}")
        migrator = get_migrator(self.db_path)
        migrator.run_migrations()

    def get_migration_status(self) -> MigrationStatus:
        """Get current migration status."""
        migrator = get_migrator(self.db_path)

        current_version = migrator.get_current_version()
        raw_history = migrator.get_migration_history()
        history = [MigrationRecord(v['version'], v['name'], v['applied_at']) for v in raw_history]

        return MigrationStatus(
            database_path=str(self.db_path),
            current_version=current_version,
            history=history,
            has_migrations=len(history) > 0
        )

    def _format_migration_display(self, status: MigrationStatus) -> str:
        """Format migration status for CLI display."""
        lines = [
            "Database Migration Status",
            "=" * 60,
            f"Database: {status.database_path}",
            f"Current Version: {status.current_version}",
            "",
        ]

        if status.history:
            lines.append("Applied Migrations:")
            lines.append("-" * 60)
            for record in status.history:
                lines.append(f"[{record.version}] {record.name}")
                lines.append(f"Applied: {record.applied_at}")
        else:
            lines.append("No migrations applied yet")

        lines.append("=" * 60)

        return "\n".join(lines)

    def get_migration_history_display(self) -> str:
        """Get formatted migration status for CLI display."""
        status = self.get_migration_status()
        return self._format_migration_display(status)
