
# Actual dev notes

This is severely work in progress, and there'll be breaking changes constantly. Don't use.

# Examples

```bash
# Start FastAPI server with qwen model, custom host/port, and keep model loaded in memory
./tts-inference.sh --model qwen run fastapi --host 0.0.0.0 --port 8080 --keep-warm --log-level DEBUG

# Generate test audio with custom parameters for expressiveness
./tts-inference.sh --model qwen test-gen --voice-id my_voice --text "Hello there!" --temperature 1.2 --top-p 0.9 --top-k 50 --repetition-penalty 1.05 --output-dir ./samples
```

# ZMQ Protocol

## Overview
The ZMQ server uses a ROUTER socket (default: `tcp://localhost:20501`) for bidirectional communication. Optionally, a PUB socket can be enabled for broadcasting responses (no identity routing).

**Connection**: ROUTER socket
- **Input** (multipart): `[identity_frames..., request_data (msgpack or JSON)]`
  - `request_data`: `{"api_key": str, "type": str, ...other_params}`
- **Output** (ROUTER mode, multipart): `[identity_frames..., msg_type (bytes), data (msgpack)]`
  - `msg_type`: `b"response" | b"error" | b"metadata" | b"audio" | b"complete"`
- **Output** (PUB mode, multipart): `[msg_type, data]`

Data prefers msgpack; falls back to JSON. All requests require valid `api_key`.

## Request Types

| Type          | Parameters                                                                 | Description                  |
|---------------|----------------------------------------------------------------------------|------------------------------|
| `synthesize`  | `TTSRequest` fields (see [schemas.py](src/tts_inference/models/schemas.py)) | Stream TTS audio             |
| `list_voices` | (none)                                                                     | List uploaded voices         |
| `upload_voice`| `voice_id`, `sample_rate`, `voice_transcript`, `audio_data` (base64 audio) | Upload new voice sample      |
| `delete_voice`| `voice_id`                                                                | Delete voice                 |
| `health`      | (none)                                                                     | Health check                 |
| `ready`       | (none)                                                                     | Readiness probe              |
| `model_unload`| (none)                                                                     | Unload TTS model             |
| `model_info`  | (none)                                                                     | Get model/sample_rate info   |

### TTSRequest Example (Qwen)
```json
{
  "text": "Hello world!",
  "voice_config": {
    "voice_id": "my_voice",
    "language": "en",
    "ref_text": "Reference text matching audio.",
    "x_vector_only": false,
    "max_new_tokens": 4096,
    "temperature": 0.9,
    "top_p": 1.0,
    "top_k": 50,
    "repetition_penalty": 1.05,
    "subtalker_dosample": true,
    "subtalker_temperature": 0.9
  },
  "audio_format": "pcm",
  "sample_rate": 24000
}
```

## Responses

**`synthesize`** sequence:
1. `metadata`: `{"status": "streaming", "sample_rate": int, "audio_format": str}`
2. Multiple `audio`: encoded chunks (base64? No, raw encoded bytes)
3. `complete`: `{"status": "complete", "chunks": int}`

**Others**:
- `response`: `{"status": "success", ...data}`
- `error`: `{"error": str}`
