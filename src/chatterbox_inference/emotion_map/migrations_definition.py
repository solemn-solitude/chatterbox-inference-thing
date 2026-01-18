"""Migration definitions for emotional prosody tables."""

import aiosqlite
from pathlib import Path
from ..models.migrations import MigrationManager

# Create the migration manager (will be initialized with db_path later)
migrator = MigrationManager(Path("placeholder"))  # Path will be set at runtime


@migrator.register(1, "create_prompt_templates_table")
async def create_prompt_templates(db: aiosqlite.Connection):
    """Create the prompt_templates table for storing emotional prompts."""
    await db.execute("""
        CREATE TABLE IF NOT EXISTS prompt_templates (
            template_id TEXT PRIMARY KEY,
            
            -- The prompt text (~15 seconds of speech, 40-60 words)
            prompt_text TEXT NOT NULL,
            
            -- Metadata for reference
            emotion_label TEXT,
            description TEXT,
            
            -- Pre-tuned generation parameters (optimal for this specific prompt)
            exaggeration REAL DEFAULT 0.15,
            cfg_weight REAL DEFAULT 0.8,
            temperature REAL DEFAULT 0.8,
            repetition_penalty REAL DEFAULT 1.2,
            
            -- Target emotional coordinates (initial estimate, refined after generation)
            target_valence REAL,
            target_arousal REAL,
            target_tension REAL,
            target_stability REAL,
            
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


@migrator.register(2, "create_emotional_anchors_table")
async def create_emotional_anchors(db: aiosqlite.Connection):
    """Create the emotional_anchors table for storing generated voice samples."""
    await db.execute("""
        CREATE TABLE IF NOT EXISTS emotional_anchors (
            anchor_id TEXT PRIMARY KEY,
            base_voice_id TEXT NOT NULL,
            template_id TEXT NOT NULL,
            
            -- File storage (path only, NOT binary data)
            audio_file_path TEXT NOT NULL,
            sample_rate INTEGER NOT NULL,
            duration_seconds REAL,
            
            -- ACTUAL emotional coordinates (assigned after generation & analysis)
            valence REAL NOT NULL,
            arousal REAL NOT NULL,
            tension REAL NOT NULL,
            stability REAL NOT NULL,
            
            -- Extracted acoustic features (for analysis & validation)
            mean_pitch REAL,
            pitch_variance REAL,
            pitch_range REAL,
            mean_energy REAL,
            energy_variance REAL,
            speaking_rate REAL,
            spectral_centroid REAL,
            
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (base_voice_id) REFERENCES voices(voice_id),
            FOREIGN KEY (template_id) REFERENCES prompt_templates(template_id)
        )
    """)


@migrator.register(3, "create_emotional_anchors_indexes")
async def create_indexes(db: aiosqlite.Connection):
    """Create indexes for efficient emotional anchor queries."""
    await db.execute("""
        CREATE INDEX IF NOT EXISTS idx_emotional_coords 
        ON emotional_anchors(valence, arousal, tension, stability)
    """)
    
    await db.execute("""
        CREATE INDEX IF NOT EXISTS idx_base_voice 
        ON emotional_anchors(base_voice_id)
    """)
    
    await db.execute("""
        CREATE INDEX IF NOT EXISTS idx_template 
        ON emotional_anchors(template_id)
    """)


def get_migrator(db_path: Path) -> MigrationManager:
    """Get a migration manager configured for the given database path.
    
    Args:
        db_path: Path to the SQLite database
        
    Returns:
        Configured MigrationManager instance
    """
    migrator.db_path = db_path
    return migrator
