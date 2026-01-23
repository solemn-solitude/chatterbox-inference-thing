"""Emotional prosody mapping system."""

from pathlib import Path

# Get the emotion_map directory path
EMOTION_MAP_DIR = Path(__file__).parent
PROMPT_TEMPLATES_SEED = EMOTION_MAP_DIR / "prompt_templates_seed.sql"
