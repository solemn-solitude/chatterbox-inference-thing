# Setup Guide - TTS Inference

Quick setup guide to get your TTS server running.

## Prerequisites

- Python 3.11+
- pip or uv package manager
- (Optional) CUDA-capable GPU for faster inference

## Installation Steps

### 1. Install Server

```bash
cd /home/lethys/boot_launching_applications/tts_test_thing
pip install -e .
```

Or with uv (faster):
```bash
uv pip install -e .
```

### 2. Install Client (Optional)

```bash
cd client
pip install -e .
```

### 3. Set API Key

**Required before starting the server!**

```bash
export CHATTERBOX_API_KEY="my-secret-key-12345"
```

Make it permanent (add to ~/.bashrc or ~/.zshrc):
```bash
echo 'export CHATTERBOX_API_KEY="my-secret-key-12345"' >> ~/.bashrc
source ~/.bashrc
```

### 4. Verify Installation

```bash
tts-inference config-info
```

Should show configuration without errors.

## Running the Server

### FastAPI Server (HTTP/WebSocket)

```bash
tts-inference run fastapi
```

Server will be available at: `http://localhost:20480`

**API Documentation**: http://localhost:20480/docs (FastAPI auto-generated)

### ZMQ Server (High Performance)

```bash
tts-inference run zmq
```

Server will listen on: `tcp://*:5555`

## First Test

### Using HTTP Client

```bash
# In a new terminal
cd examples
export CHATTERBOX_API_KEY="my-secret-key-12345"
python example_usage.py
```

### Using curl

```bash
curl -X POST "http://localhost:20480/tts/synthesize" \
  -H "Authorization: Bearer my-secret-key-12345" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, this is a test!",
    "voice_mode": "default",
    "voice_config": {"speed": 1.0},
    "audio_format": "pcm"
  }' \
  --output test_audio.pcm
```

## Voice Cloning Setup

### 1. Prepare Voice Reference

- Format: WAV file
- Sample rate: 24000 Hz or higher
- Duration: 3-10 seconds recommended
- Content: Clear speech, low background noise

### 2. Upload Voice

```bash
curl -X POST "http://localhost:20480/voices/upload" \
  -H "Authorization: Bearer my-secret-key-12345" \
  -F "voice_id=my_voice" \
  -F "sample_rate=24000" \
  -F "audio_file=@reference_audio.wav"
```

### 3. Use Cloned Voice

```bash
curl -X POST "http://localhost:20480/tts/synthesize" \
  -H "Authorization: Bearer my-secret-key-12345" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "This uses my cloned voice!",
    "voice_mode": "clone",
    "voice_config": {"voice_id": "my_voice", "speed": 1.0},
    "audio_format": "pcm"
  }' \
  --output cloned_audio.pcm
```

## Troubleshooting

### "API key must be set"

Make sure you've exported the API key:
```bash
export CHATTERBOX_API_KEY="your-key"
```

### "Failed to load ChatterTTS model"

- Check if you have enough memory (8GB+ RAM recommended)
- Verify chatterbox-tts is installed: `pip list | grep chatterbox`
- Install if missing: `pip install chatterbox-tts`

### "Connection refused"

- Ensure server is running: `ps aux | grep chatterbox`
- Check correct port: FastAPI (20480) or ZMQ (5555)
- Verify no firewall blocking

### Voice Upload Fails

- Ensure WAV format (not MP3, OGG, etc.)
- Check file permissions
- Verify voice_id is unique (check with `/voices/list`)

## Advanced Configuration

### Custom Ports

```bash
# FastAPI on port 9000
tts-inference run fastapi --port 9000

# ZMQ on port 6666
tts-inference run zmq --port 6666
```

### Custom Voice Directory

```bash
export CHATTERBOX_VOICE_DIR="/path/to/voices"
tts-inference run fastapi
```

### Debug Logging

```bash
tts-inference run fastapi --log-level DEBUG
```

## Production Deployment

### Using Systemd

1. Create service file: `/etc/systemd/system/tts-inference.service`

```ini
[Unit]
Description=TTS Inference TTS Server
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/home/your-user/tts-inference
Environment="CHATTERBOX_API_KEY=your-production-key"
ExecStart=/usr/local/bin/tts-inference run fastapi
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

2. Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable tts-inference
sudo systemctl start tts-inference
sudo systemctl status tts-inference
```

### Using Docker (Future)

Docker support can be added with a Dockerfile:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -e .
ENV CHATTERBOX_API_KEY=""
CMD ["tts-inference", "run", "fastapi", "--host", "0.0.0.0"]
```

## Next Steps

1. **Explore API**: Visit http://localhost:20480/docs for interactive API documentation
2. **Upload Voices**: Add custom voice references for cloning
3. **Integrate**: Use the client library in your applications
4. **Monitor**: Check logs and health endpoints regularly

## Support

- Check README.md for detailed documentation
- See examples/ directory for code samples
- Review API docs at /docs endpoint
