from dataclasses import dataclass
import numpy as np


@dataclass
class MigrationRecord:
    version: str
    name: str
    applied_at: str


@dataclass
class MigrationStatus:
    database_path: str
    current_version: str | int
    history: list[MigrationRecord]
    has_migrations: bool


@dataclass
class ModelStatus:
    model_loaded: bool
    voice_dir_accessible: bool
    database_accessible: bool


@dataclass
class UnloadResult:
    success: bool
    message: str
    was_loaded: bool


@dataclass
class VoiceRecord:
    voice_id: str
    filename: str
    sample_rate: int
    voice_transcript: str | None = None
    duration_seconds: float | None = None
    uploaded_at: str | None = None


@dataclass
class TestSamplesFile:
    path: str
    size: int


@dataclass
class TestSamplesResult:
    sample_rate: int
    duration: float
    samples: int
    files: dict[str, TestSamplesFile]


@dataclass
class ChatterboxParams:
    text: str
    voice_id: str
    voice_reference: np.ndarray
    speed: float
    sample_rate: int
    use_turbo: bool
    exaggeration: float
    cfg_weight: float
    temperature: float
    repetition_penalty: float
