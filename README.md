# Chatterbox Inference Server

A production-ready TTS (Text-to-Speech) inference server with streaming support, built on [Chatterbox TTS](https://github.com/resemble-ai/chatterbox).

## Features

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

- **TTS Engine**: ChatterTTS wrapper with voice cloning
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
chatterbox-inference run fastapi
```

**ZMQ Mode:**
```bash
chatterbox-inference run zmq
```

### 3. Use Client

```python
from chatterbox_inference_client import Client

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
| `CHATTERBOX_VOICE_DIR` | Voice storage directory | `~/.local/chatterbox-inference` |
| `CHATTERBOX_FASTAPI_HOST` | FastAPI bind host | `0.0.0.0` |
| `CHATTERBOX_FASTAPI_PORT` | FastAPI port | `20480` |
| `CHATTERBOX_ZMQ_HOST` | ZMQ bind host | `*` |
| `CHATTERBOX_ZMQ_PORT` | ZMQ port | `5555` |
| `CHATTERBOX_LOG_LEVEL` | Logging level | `INFO` |

### CLI Options

```bash
# View configuration
chatterbox-inference config-info

# Run with custom settings
chatterbox-inference run fastapi --host 127.0.0.1 --port 8080 --log-level DEBUG
chatterbox-inference run zmq --port 5556
```

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
from chatterbox_inference_client import Client

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
chatterbox-inference run fastapi --reload
```

### Project Structure

```
tts_test_thing/
├── src/chatterbox_inference/
│   ├── auth/           # API key authentication
│   ├── models/         # Pydantic schemas & database
│   ├── server/         # FastAPI & ZMQ servers
│   ├── tts/            # TTS engine & voice management
│   ├── utils/          # Config & audio utilities
│   └── cli.py          # Click CLI
├── client/             # Separate client package
│   └── src/chatterbox_inference_client/
│       ├── base.py     # Abstract client
│       ├── http_client.py
│       ├── zmq_client.py
│       └── exceptions.py
└── README.md
```

## Production Deployment

### FastAPI with Gunicorn

```bash
gunicorn chatterbox_inference.server.fastapi_server:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:20480
```

### Systemd Service

```ini
[Unit]
Description=Chatterbox Inference Server
After=network.target

[Service]
Type=simple
User=chatterbox
Environment="CHATTERBOX_API_KEY=your-secret-key"
ExecStart=/usr/local/bin/chatterbox-inference run fastapi
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
- Verify server is running: `chatterbox-inference config-info`
- Increase ZMQ timeout in client code

## License

See LICENSE file for details.

## Contributing

Contributions welcome! Please open an issue or pull request.

## Credits

Built on [Chatterbox TTS](https://github.com/resemble-ai/chatterbox) by Resemble AI.
