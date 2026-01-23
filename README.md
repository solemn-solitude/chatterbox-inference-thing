# TTS Inference Server

A production-ready TTS (Text-to-Speech) inference server with streaming support, supporting multiple TTS models including Chatterbox and Qwen3-TTS.

## Features

- **Multiple TTS Models**: Support for ChatterboxTTS and Qwen3-TTS with easy switching
- **Voice Caching**: Qwen3-TTS caches voice prompts for 3-5x faster subsequent generations
- **Dual Server Modes**: FastAPI (HTTP/WebSocket) and ZMQ for different use cases
- **Streaming Audio**: Real-time audio streaming for low latency
- **Voice Cloning**: Upload and use custom voice references
- **Multiple Audio Formats**: PCM and Vorbis (Ogg) support
- **API Key Authentication**: Secure access control
- **Persistent Storage**: SQLite database for voice metadata
- **Client Library**: Separate Python client for easy integration

## Architecture

### Server Modes

1. **FastAPI Server** (HTTP/WebSocket)
   - REST API endpoints
   - WebSocket for bidirectional streaming
   - Best for: Web applications, remote access
   - Port: 20480 (default)

2. **ZMQ Server** (ROUTER/DEALER)
   - High-performance messaging
   - Multiple concurrent clients
   - Best for: Local network, microservices
   - Port: 5555 (default)

### Components

- **TTS Abstraction**: Unified interface supporting ChatterboxTTS and Qwen3-TTS
- **ChatterboxTTS Engine**: Original ChatterboxTTS wrapper with turbo support
- **Qwen3-TTS Engine**: New Qwen3-TTS with voice prompt caching (3-5x faster)
- **Voice Manager**: Upload, store, and manage voice references
- **Audio Streaming**: PCM/Vorbis encoding with chunked streaming
- **Database**: SQLite for voice metadata (sample rates, durations)

## Installation

### Server

```bash
cd /path/to/tts_test_thing
pip install -e .
```

### Client (Optional)

```bash
cd /path/to/tts_test_thing/client
pip install -e .
```

## Quick Start

### 1. Set API Key

```bash
export CHATTERBOX_API_KEY="your-secret-api-key-here"
```

### 2. Run Server

**FastAPI Mode:**
```bash
tts-inference run fastapi
```

**ZMQ Mode:**
```bash
tts-inference run zmq
```

### 3. Use Client

```python
from tts_inference_client import Client

# HTTP client
client = Client.http("http://localhost:20480", api_key="your-api-key")

# Synthesize speech
for audio_chunk in client.synthesize("Hello, world!"):
    # Process audio chunk
    pass

client.close()
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CHATTERBOX_API_KEY` | API key for authentication | *Required* |
| `CHATTERBOX_TTS_MODEL` | TTS model: `chatterbox` or `qwen` | `chatterbox` |
| `CHATTERBOX_QWEN_CACHE_TTL` | Qwen voice cache TTL in minutes | `60` |
| `CHATTERBOX_VOICE_DIR` | Voice storage directory | `~/.local/share/tts-inference` |
| `CHATTERBOX_FASTAPI_HOST` | FastAPI bind host | `0.0.0.0` |
| `CHATTERBOX_FASTAPI_PORT` | FastAPI port | `20480` |
| `CHATTERBOX_ZMQ_HOST` | ZMQ bind host | `*` |
| `CHATTERBOX_ZMQ_PORT` | ZMQ port | `5555` |
| `CHATTERBOX_LOG_LEVEL` | Logging level | `INFO` |

### CLI Options

```bash
# View configuration
tts-inference config-info

# Run with specific TTS model
tts-inference run fastapi --model qwen
tts-inference run zmq --model chatterbox

# Run with custom settings
tts-inference run fastapi --host 127.0.0.1 --port 8080 --log-level DEBUG
tts-inference run zmq --port 5556 --model qwen --keep-warm
```

### TTS Model Selection

The server supports multiple TTS models via the `CHATTERBOX_TTS_MODEL` environment variable or `--model` CLI option:

**ChatterboxTTS** (Default)
- High-quality synthesis
- Voice cloning support
- Turbo mode available
- Parameters: `exaggeration`, `cfg_weight`, `temperature`, `repetition_penalty`, `speed`

**Qwen3-TTS**
- Excellent voice quality with natural language voice descriptions
- Voice caching for 3-5x faster subsequent generations
- Support for 10 languages
- Parameters: `voice_description`, `language`, `max_new_tokens`, `top_p`, `top_k`, `temperature`

See `TTS_ABSTRACTION.md` for detailed usage examples and parameter documentation.

## API Endpoints (FastAPI)

### TTS Endpoints

**POST /tts/synthesize** - Streaming TTS synthesis
```json
{
  "text": "Text to synthesize",
  "voice_mode": "default",
  "voice_config": {
    "voice_name": "default",
    "speed": 1.0
  },
  "audio_format": "pcm",
  "sample_rate": 24000
}
```

**WS /tts/stream** - WebSocket streaming

### Voice Management

**POST /voices/upload** - Upload voice reference (multipart/form-data)
- `voice_id`: Unique identifier
- `sample_rate`: Audio sample rate
- `audio_file`: WAV file

**GET /voices/list** - List all voices

**DELETE /voices/{voice_id}** - Delete voice

### Health & Monitoring

**GET /health** - Health check

**GET /ready** - Readiness check

## Voice Cloning

### Upload a Voice

```bash
curl -X POST http://localhost:20480/voices/upload \
  -H "Authorization: Bearer your-api-key" \
  -F "voice_id=my_voice" \
  -F "sample_rate=24000" \
  -F "audio_file=@reference.wav"
```

### Use Cloned Voice

```python
client = Client.http("http://localhost:20480", "your-api-key")

for chunk in client.synthesize(
    text="Hello with cloned voice!",
    voice_mode="clone",
    voice_id="my_voice"
):
    # Process audio
    pass
```

## ZMQ Protocol

### Message Format

**Request:**
```
[b"", request_json]
```

**Response:**
```
[b"", msg_type, data]
```

### Message Types

- `metadata`: Streaming metadata (sample_rate, format)
- `audio`: Audio chunk (binary)
- `complete`: Synthesis complete
- `error`: Error message
- `response`: General response

### Request Types

```json
{
  "type": "synthesize",
  "api_key": "your-key",
  "text": "Hello",
  "voice_mode": "default",
  "voice_config": {"speed": 1.0},
  "audio_format": "pcm"
}
```

```json
{
  "type": "list_voices",
  "api_key": "your-key"
}
```

```json
{
  "type": "health",
  "api_key": "your-key"
}
```

## Client Library

See `client/README.md` for detailed client documentation.

### Quick Example

```python
from tts_inference_client import Client

# HTTP Client
with Client.http("http://localhost:20480", "api-key") as client:
    for chunk in client.synthesize("Hello!"):
        print(f"Received {len(chunk)} bytes")

# ZMQ Client
with Client.zmq("tcp://localhost:5555", "api-key") as client:
    for chunk in client.synthesize("Hello!"):
        print(f"Received {len(chunk)} bytes")
```

## Development

### Running Tests

```bash
# Set API key for testing
export CHATTERBOX_API_KEY="test-key"

# Run server in development mode
tts-inference run fastapi --reload
```

### Project Structure

```
tts_test_thing/
├── src/tts_inference/
│   ├── auth/           # API key authentication
│   ├── models/         # Pydantic schemas & database
│   ├── server/         # FastAPI & ZMQ servers
│   ├── tts/            # TTS engine & voice management
│   ├── utils/          # Config & audio utilities
│   └── cli.py          # Click CLI
├── client/             # Separate client package
│   └── src/tts_inference_client/
│       ├── base.py     # Abstract client
│       ├── http_client.py
│       ├── zmq_client.py
│       └── exceptions.py
└── README.md
```

## Production Deployment

### FastAPI with Gunicorn

```bash
gunicorn tts_inference.server.fastapi_server:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:20480
```

### Systemd Service

```ini
[Unit]
Description=TTS Inference Server
After=network.target

[Service]
Type=simple
User=chatterbox
Environment="CHATTERBOX_API_KEY=your-secret-key"
ExecStart=/usr/local/bin/tts-inference run fastapi
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

## Troubleshooting

### Model Loading Issues

- Ensure sufficient GPU memory (CUDA) or CPU RAM
- Check PyTorch installation
- Verify chatterbox-tts is installed correctly

### Voice Cloning Not Working

- Ensure WAV file is valid (mono, 16-bit)
- Sample rate should be 24kHz or higher
- Audio should be 3-10 seconds for best results

### Connection Timeouts

- Check firewall settings
- Verify server is running: `tts-inference config-info`
- Increase ZMQ timeout in client code

## License

See LICENSE file for details.

## Contributing

Contributions welcome! Please open an issue or pull request.

## Credits

Built on [Chatterbox TTS](https://github.com/resemble-ai/chatterbox) by Resemble AI.
