# TTS Abstraction System

## Overview

The tts-inference project now supports multiple TTS models through a unified abstraction layer. This allows easy switching between different TTS engines (ChatterboxTTS and Qwen3-TTS) without changing application code.

## Architecture

### Components

1. **Abstract Base Class** (`src/tts_inference/tts/base_tts.py`)
   - Defines the interface all TTS engines must implement
   - Methods: `initialize()`, `synthesize_streaming()`, `synthesize()`, `offload_model()`

2. **Engine Implementations**
   - `ChatterboxTTSEngine` - Original ChatterboxTTS with turbo support
   - `QwenTTSEngine` - New Qwen3-TTS with voice prompt caching

3. **Engine Factory** (`src/tts_inference/tts/engine.py`)
   - Creates appropriate engine based on configuration
   - Manages global engine instance

4. **Voice Caching** (`src/tts_inference/tts/qwen_voice_cache.py`)
   - Caches voice clone prompts for Qwen3-TTS
   - 3-5x faster subsequent generations

## Supported Models

### ChatterboxTTS (Default)

**Models:**
- `chatterbox` - Regular ChatterboxTTS
- `chatterbox-turbo` - Faster ChatterboxTurboTTS

**Parameters:**
- `exaggeration` (0.0-1.0) - Expressiveness level
- `cfg_weight` (0.0-1.0) - Classifier-free guidance weight
- `temperature` (0.1-2.0) - Sampling temperature
- `repetition_penalty` (1.0-2.0) - Repetition penalty
- `speed` (0.1-3.0) - Speech speed multiplier

**Streaming:** Fake streaming (generates complete audio, then chunks)

### Qwen3-TTS

**Models:**
- `qwen` - Qwen3-TTS with VoiceDesign + Base model approach

**Parameters:**
- `voice_description` - Natural language voice description
- `language` - Language or "Auto"
- `max_new_tokens` (1-8192) - Maximum tokens
- `top_p` (0.0-1.0) - Top-p sampling
- `top_k` (1-100) - Top-k sampling
- `temperature` (0.1-2.0) - Sampling temperature
- `repetition_penalty` (1.0-2.0) - Repetition penalty

**Streaming:** Chunks complete audio (can be upgraded to true streaming)

**Voice Caching:**
- First generation: Creates voice prompt (slow, ~3-5s)
- Subsequent generations: Uses cached prompt (fast, ~0.5-1s)
- Cache TTL: 60 minutes (configurable)

## Usage

### Environment Variables

```bash
# Select TTS model (default: chatterbox)
export CHATTERBOX_TTS_MODEL=qwen

# Qwen-specific settings
export CHATTERBOX_QWEN_CACHE_TTL=60  # minutes

# Common settings
export CHATTERBOX_OFFLOAD_TIMEOUT=600
export CHATTERBOX_KEEP_WARM=false
```

### CLI

```bash
# Run with ChatterboxTTS (default)
tts-inference run fastapi --model chatterbox
tts-inference run zmq --model chatterbox

# Run with Qwen3-TTS
tts-inference run fastapi --model qwen
tts-inference run zmq --model qwen

# With other options
tts-inference run fastapi --model qwen --host 0.0.0.0 --port 20480 --keep-warm
```

### API Usage

#### ChatterboxTTS Request

```python
from tts_inference_client import ChatterboxInferenceClient
from tts_inference_client.schemas import ChatterboxVoiceConfig

client = ChatterboxInferenceClient()

# Configure ChatterboxTTS
voice_config = ChatterboxVoiceConfig(
    voice_name="default",
    exaggeration=0.5,
    cfg_weight=0.5,
    temperature=0.8,
    repetition_penalty=1.2,
    speed=1.0
)

# Generate
result = await client.generate_speech(
    text="Hello world!",
    voice_config=voice_config,
    voice_mode="default",
    audio_format="wav",
    use_turbo=False
)
```

#### Qwen3-TTS Request

```python
from tts_inference_client import ChatterboxInferenceClient
from tts_inference_client.schemas import QwenVoiceConfig

client = ChatterboxInferenceClient()

# Configure Qwen3-TTS
voice_config = QwenVoiceConfig(
    voice_id="solar",
    voice_description="Young male voice, energetic and enthusiastic",
    language="Auto",
    temperature=0.9,
    top_p=1.0,
    top_k=50,
    repetition_penalty=1.05,
    speed=1.0  # Not supported by Qwen, will warn
)

# Generate (first call - creates voice prompt)
result = await client.generate_speech(
    text="Hello world!",
    voice_config=voice_config,
    voice_mode="clone",
    audio_format="wav",
    model_type="qwen"
)

# Generate again (uses cached prompt - much faster!)
result2 = await client.generate_speech(
    text="This is much faster now!",
    voice_config=voice_config,
    voice_mode="clone",
    audio_format="wav",
    model_type="qwen"
)
```

### Voice Caching Workflow

Qwen3-TTS uses a two-stage voice creation process:

1. **VoiceDesign Stage** (first request only):
   ```
   User Request: voice_description="Young male, energetic"
   ↓
   VoiceDesign Model: Creates reference audio from description
   ↓
   Base Model: Extracts voice features → Creates prompt
   ↓
   Cache: Stores prompt for reuse
   ```
   Time: ~3-5 seconds

2. **Generation Stage** (all requests):
   ```
   User Request: voice_id="solar", text="Hello world"
   ↓
   Cache Check: Finds cached prompt
   ↓
   Base Model: Uses cached prompt for generation
   ↓
   Output: Generated audio
   ```
   Time: ~0.5-1 second (after first request)

**Benefits:**
- 3-5x faster subsequent generations
- Consistent voice across multiple utterances
- Easy to add new voices via natural language descriptions

### Predefined Voices

Qwen3-TTS comes with predefined voices:

```python
# Use predefined voice
voice_config = QwenVoiceConfig(
    voice_id="solar",
    voice_description="Young male voice, energetic and enthusiastic",
    # voice_description is automatically filled for predefined voices
)
```

Available predefined voices:
- `solar` - Young male, energetic and enthusiastic
- `default` - Natural speaking voice

Add more in `src/tts_inference/tts/qwen_tts.py`:

```python
PREDEFINED_VOICES = {
    "solar": "Young male voice, energetic and enthusiastic...",
    "luna": "Young female voice, gentle and soft-spoken...",
    "narrator": "Deep male voice, authoritative and calm...",
}
```

## Schema Hierarchy

```
BaseVoiceConfig
├── ChatterboxVoiceConfig
│   ├── exaggeration
│   ├── cfg_weight
│   ├── temperature
│   └── repetition_penalty
└── QwenVoiceConfig
    ├── voice_description
    ├── language
    ├── instruct
    ├── ref_text
    ├── max_new_tokens
    ├── top_p
    ├── top_k
    ├── temperature
    └── repetition_penalty
```

## Configuration

All configuration is centralized in `src/tts_inference/utils/config.py`:

```python
class Config:
    # TTS Model selection
    tts_model = "chatterbox"  # or "qwen"
    
    # Qwen cache settings
    qwen_cache_ttl = 60  # minutes
    
    # Common settings
    offload_timeout = 600  # seconds
    keep_warm = False
```

## Installation

```bash
# Install dependencies
uv sync

# Or with pip
pip install -e .
```

## Performance Comparison

| Model | First Gen | Subsequent Gen | Quality |
|-------|-----------|-----------------|---------|
| Chatterbox | ~2-3s | ~2-3s | High |
| Chatterbox Turbo | ~1-2s | ~1-2s | Good |
| Qwen3-TTS | ~3-5s | ~0.5-1s | Excellent |

## Troubleshooting

### Model Not Loading

```bash
# Check which model is selected
export CHATTERBOX_TTS_MODEL=chatterbox

# Or via CLI
tts-inference run fastapi --model chatterbox
```

### Cache Issues

```python
# Clear Qwen voice cache programmatically
from tts_inference.tts import get_tts_engine

engine = get_tts_engine()
if hasattr(engine, 'clear_voice_cache'):
    engine.clear_voice_cache()

# Or invalidate specific voice
if hasattr(engine, 'invalidate_voice'):
    engine.invalidate_voice('solar')
```

### Import Errors

Ensure qwen-tts is installed:
```bash
pip install qwen-tts
```

## Future Enhancements

- [ ] True streaming for Qwen3-TTS (currently chunks complete audio)
- [ ] Per-voice cache TTL configuration
- [ ] Cache statistics API endpoint
- [ ] Voice prompt export/import
- [ ] Additional predefined voices
- [ ] Dynamic voice creation via API

## Contributing

To add a new TTS model:

1. Create new engine class inheriting from `BaseTTSEngine`
2. Implement all abstract methods
3. Add model-specific config class inheriting from `BaseVoiceConfig`
4. Update engine factory to create new engine type
5. Add to CLI choices
6. Update documentation

Example:
```python
from .base_tts import BaseTTSEngine

class MyTTSEngine(BaseTTSEngine):
    async def initialize(self):
        # Load model
        pass
    
    @property
    def sample_rate(self) -> int:
        return 24000
    
    def is_loaded(self) -> bool:
        return self.model is not None
    
    async def offload_model(self):
        # Release model
        pass
    
    async def synthesize_streaming(
        self, text, voice_mode, voice_reference, voice_name, speed, sample_rate, **model_params
    ):
        # Generate audio
        pass