# TTS Inference Client

Python client library for connecting to TTS Inference server via HTTP or ZMQ.

## Installation

```bash
pip install -e .
```

## Quick Start

### HTTP Client

```python
from tts_inference_client import Client

# Create client
client = Client.http("http://localhost:20480", api_key="your-api-key")

# Synthesize speech (streaming)
for audio_chunk in client.synthesize("Hello, world!"):
    # Process audio chunk (e.g., play, save, etc.)
    print(f"Received {len(audio_chunk)} bytes")

# List voices
voices = client.list_voices()
print(f"Available voices: {voices}")

# Upload voice reference
response = client.upload_voice(
    voice_id="my_voice",
    audio_file_path="reference.wav",
    sample_rate=24000
)

# Use cloned voice
for chunk in client.synthesize(
    text="Hello with my voice!",
    voice_mode="clone",
    voice_id="my_voice"
):
    print(f"Chunk: {len(chunk)} bytes")

# Clean up
client.close()
```

### ZMQ Client

```python
from tts_inference_client import Client

# Create ZMQ client
client = Client.zmq("tcp://localhost:5555", api_key="your-api-key")

# Synthesize (same API as HTTP)
for audio_chunk in client.synthesize("Hello via ZMQ!"):
    print(f"Received {len(audio_chunk)} bytes")

client.close()
```

### Context Manager

```python
from tts_inference_client import Client

# Automatically closes connection
with Client.http("http://localhost:20480", "api-key") as client:
    for chunk in client.synthesize("Hello!"):
        process_audio(chunk)
```

## API Reference

### Client Factory

**`Client.http(server_url, api_key)`**
- Create HTTP/REST client
- `server_url`: e.g., `"http://localhost:20480"`
- `api_key`: Your API key

**`Client.zmq(server_url, api_key)`**
- Create ZMQ client
- `server_url`: e.g., `"tcp://localhost:5555"`
- `api_key`: Your API key

### Common Methods

All clients implement these methods:

**`synthesize(text, voice_mode="default", voice_name=None, voice_id=None, audio_format="pcm", sample_rate=None, speed=1.0)`**
- Synthesize speech with streaming
- Returns: Iterator of audio chunks (bytes)
- Parameters:
  - `text`: Text to synthesize
  - `voice_mode`: `"default"` or `"clone"`
  - `voice_name`: Name of default voice (for default mode)
  - `voice_id`: ID of cloned voice (for clone mode)
  - `audio_format`: `"pcm"` or `"vorbis"`
  - `sample_rate`: Output sample rate (None = use model default)
  - `speed`: Speech speed multiplier (0.1 to 3.0)

**`list_voices()`**
- List all available voices
- Returns: Dict with voice information

**`health_check()`**
- Check server health
- Returns: Dict with health status

**`close()`**
- Close client connection

### HTTP-Only Methods

**`upload_voice(voice_id, audio_file_path, sample_rate)`**
- Upload voice reference file
- Parameters:
  - `voice_id`: Unique identifier
  - `audio_file_path`: Path to WAV file
  - `sample_rate`: Sample rate of audio
- Returns: Upload response dict

**`delete_voice(voice_id)`**
- Delete a voice reference
- Returns: Deletion response dict

## Examples

### Save Audio to File

```python
from tts_inference_client import Client

with Client.http("http://localhost:20480", "api-key") as client:
    with open("output.pcm", "wb") as f:
        for chunk in client.synthesize("Save this audio"):
            f.write(chunk)
```

### Stream to Audio Player

```python
import pyaudio
from tts_inference_client import Client

# Setup pyaudio
p = pyaudio.PyAudio()
stream = p.open(
    format=pyaudio.paInt16,
    channels=1,
    rate=24000,
    output=True
)

# Stream and play
with Client.http("http://localhost:20480", "api-key") as client:
    for chunk in client.synthesize("Play this in real-time!"):
        stream.write(chunk)

stream.close()
p.terminate()
```

### Voice Cloning Workflow

```python
from tts_inference_client import Client

client = Client.http("http://localhost:20480", "api-key")

# 1. Upload voice reference
print("Uploading voice reference...")
response = client.upload_voice(
    voice_id="celebrity_voice",
    audio_file_path="celebrity_sample.wav",
    sample_rate=24000
)
print(f"Upload: {response}")

# 2. List voices to confirm
voices = client.list_voices()
print(f"Available voices: {voices['total']}")

# 3. Use the cloned voice
print("Synthesizing with cloned voice...")
audio_data = b""
for chunk in client.synthesize(
    text="This should sound like the celebrity!",
    voice_mode="clone",
    voice_id="celebrity_voice",
    speed=1.1
):
    audio_data += chunk

print(f"Generated {len(audio_data)} bytes of audio")

# 4. Cleanup (optional)
# client.delete_voice("celebrity_voice")

client.close()
```

## Error Handling

```python
from tts_inference_client import (
    Client,
    AuthenticationError,
    ConnectionError,
    RequestError,
    StreamingError
)

try:
    client = Client.http("http://localhost:20480", "wrong-key")
    for chunk in client.synthesize("Test"):
        pass
except AuthenticationError as e:
    print(f"Auth failed: {e}")
except ConnectionError as e:
    print(f"Connection failed: {e}")
except RequestError as e:
    print(f"Request error: {e}")
except StreamingError as e:
    print(f"Streaming error: {e}")
finally:
    client.close()
```

## Protocol Comparison

### When to Use HTTP

- Remote access over internet
- Web application integration
- RESTful API preferred
- File uploads needed (voice cloning)
- Lower throughput requirements

### When to Use ZMQ

- Local network deployment
- High-performance requirements
- Microservices architecture
- Multiple concurrent clients
- Low-latency critical

## Dependencies

- `pyzmq>=26.0` - ZMQ client
- `requests>=2.31.0` - HTTP client
- `websockets>=13.0` - WebSocket support
- `pydantic>=2.0` - Data validation

## License

See LICENSE file.
