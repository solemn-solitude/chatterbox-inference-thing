# TTS System Analysis - Potential Issues

## Analysis Date
January 23, 2026

## Scope
Analyzing the complete flow from ZMQ input to ZMQ output, focusing on qwen3-tts integration and excluding emotional prosody/emotion_map features.

---

## Critical Issues

### 1. **Missing Union Import in schemas.py** ⚠️ HIGH PRIORITY
**Location:** `src/tts_inference/models/schemas.py:39`

**Problem:**
```python
voice_config: Union[ChatterboxVoiceConfig, QwenVoiceConfig] = Field(...)
```
The `Union` type is used but not imported from `typing`.

**Impact:** This will cause an immediate runtime error when the schema is loaded.

**Fix:** Add `Union` to the imports:
```python
from typing import Optional, Literal, Union
```

---

### 2. **Plain Text ZMQ Handler Uses Wrong Voice Config** ⚠️ HIGH PRIORITY
**Location:** `src/tts_inference/server/zmq_server.py:155-167`

**Problem:**
When plain text is received via ZMQ (non-JSON), it creates a hardcoded request:
```python
request_dict = {
    "text": text,
    "voice_mode": "clone",
    "audio_format": "pcm",
    "voice_config": {
        "voice_id": "solar",  # Hardcoded voice_id
        "speed": 1.0,
        "exaggeration": 0.15,  # Chatterbox-specific
        "cfg_weight": 1       # Chatterbox-specific
    },
    "use_turbo": False
}
```

**Issues:**
1. Doesn't specify `model_type`, so uses server default (could be qwen or chatterbox)
2. Uses Chatterbox-specific parameters (exaggeration, cfg_weight) 
3. If server is configured for qwen, these parameters won't work properly
4. The voice_id "solar" is referenced but only works if it's in PREDEFINED_VOICES for qwen

**Impact:** Plain text requests will fail or behave unexpectedly if server is using qwen3-tts.

**Fix Options:**
- Option A: Detect server model type and create appropriate config
- Option B: Always specify model_type in plain text handler
- Option C: Remove plain text handler (enforce JSON-only)

---

### 3. **Voice Configuration Type Mismatch in TTSService** ⚠️ MEDIUM PRIORITY
**Location:** `src/tts_inference/services/tts_service.py:45-67`

**Problem:**
```python
params = {
    "speed": request.voice_config.speed,
    "sample_rate": request.sample_rate
}

if isinstance(request.voice_config, ChatterboxVoiceConfig):
    params.update({...})
elif isinstance(request.voice_config, QwenVoiceConfig):
    params.update({
        "voice_id": request.voice_config.voice_id,  # This is critical for qwen
        ...
    })
```

But the base parameters include `voice_name` from `request.voice_config.voice_name` which is inherited from BaseVoiceConfig. Both configs have `voice_id`, which could cause confusion.

**Issue:** When engine.synthesize_streaming is called, it receives mixed parameters that work for both models, but the voice_id might not be set if ChatterboxVoiceConfig is used with qwen engine.

**Impact:** If someone manually sets model_type="qwen" but uses ChatterboxVoiceConfig, voice_id won't be passed and synthesis will fail.

---

### 4. **Qwen Voice Selection Logic Has Multiple Failure Paths** ⚠️ MEDIUM PRIORITY
**Location:** `src/tts_inference/tts/qwen_tts.py:229-280`

**Problem:**
The voice selection logic has complex branching:
```python
if voice_id and voice_description:
    # Path 1: Cached VoiceDesign
elif voice_id and voice_reference is not None:
    # Path 2: Direct cloning with cache
elif voice_name and voice_name.lower() in PREDEFINED_VOICES:
    # Path 3: Predefined voices
elif voice_description:
    # Path 4: VoiceDesign without ID (generates hash-based ID)
else:
    raise ValueError(...)
```

**Issues:**
1. Path 2 (`voice_id and voice_reference`) expects `voice_reference` parameter, but parameter name in function signature is `voice_reference`, which matches
2. The "solar" voice is referenced in the plain text handler but only exists in PREDEFINED_VOICES if explicitly defined
3. Path 4 generates an ID from hash, which could collide or be hard to track
4. No path handles the case where voice_id is provided alone without description or reference

**Current PREDEFINED_VOICES:**
```python
PREDEFINED_VOICES = {
    "solar": "Young male voice, energetic and enthusiastic...",
    "default": "Natural speaking voice..."
}
```

**Impact:** 
- If plain text handler uses qwen with voice_id="solar", it will fail because voice_description is not provided
- Path 4's auto-generated IDs could cause cache collisions

---

### 5. **Model Type Not Propagated in Plain Text Handler** ⚠️ MEDIUM PRIORITY
**Location:** `src/tts_inference/server/zmq_server.py:155-167`

**Problem:**
The plain text handler doesn't specify `model_type` in the request_dict, so it relies on CONFIG.tts_model default. This means:

1. If CONFIG.tts_model is "qwen", the request will use qwen engine
2. But the voice_config structure is Chatterbox-specific
3. This will cause a mismatch when TTSService tries to parse it

**Example flow:**
1. Plain text "Hello" arrives
2. Creates request with Chatterbox-style config
3. But server default is qwen
4. TTSService.synthesize_streaming creates qwen engine
5. Tries to extract QwenVoiceConfig parameters from ChatterboxVoiceConfig
6. Missing voice_description or valid voice selection path
7. **FAILURE**

---

### 6. **Voice Reference Parameter Handling** ⚠️ LOW PRIORITY
**Location:** `src/tts_inference/tts/qwen_tts.py:171,229`

**Problem:**
The synthesize_streaming signature has:
```python
voice_reference: Optional[np.ndarray] = None,
```

And later uses:
```python
elif voice_id and voice_reference is not None:
    voice_prompt = await self._ensure_voice_prompt(
        voice_id=voice_id,
        reference_audio=voice_reference,  # Parameter renamed here
        ...
    )
```

The parameter is correctly passed as `reference_audio` to `_ensure_voice_prompt`, so this is actually fine. Not an issue.

---

### 7. **Speed Parameter Not Supported by Qwen** ℹ️ INFO
**Location:** `src/tts_inference/tts/qwen_tts.py:206-207`

**Current Behavior:**
```python
if speed != 1.0:
    logger.warning("Qwen3-TTS does not support speed adjustment, ignoring speed parameter")
```

This is correct - just logs a warning and continues. Not a bug, but users should be aware.

---

### 8. **Voice Mode "clone" Required But Not Enforced** ⚠️ LOW PRIORITY
**Location:** `src/tts_inference/models/schemas.py:70-73`

**Problem:**
```python
def model_post_init(self, __context):
    if self.voice_mode == "default" and not self.voice_config.voice_name:
        self.voice_config.voice_name = "default"
    elif self.voice_mode == "clone" and not self.voice_config.voice_id:
        raise ValueError("voice_id is required when voice_mode is 'clone'")
```

For Qwen, the voice_mode distinction is less clear because:
- Qwen ALWAYS does some form of cloning (even for predefined voices)
- The "default" mode with voice_name needs the voice_name to be in PREDEFINED_VOICES
- But if voice_mode="default" and voice_name="solar", it won't require voice_id
- This could work IF "solar" is in PREDEFINED_VOICES

**Impact:** Minor - the validation logic doesn't perfectly match Qwen's requirements, but it's workable.

---

## Flow Analysis

### Complete Request Flow for Qwen3-TTS

#### Path 1: JSON Request with Qwen Config
```
Client sends JSON:
{
  "type": "synthesize",
  "api_key": "...",
  "text": "Hello world",
  "model_type": "qwen",
  "voice_mode": "default",
  "voice_config": {
    "voice_name": "solar",
    "speed": 1.0,
    "voice_description": "Young male voice..."  # Optional for predefined
  }
}

↓ zmq_server.py: _handle_request
  ↓ Parses JSON ✓
  ↓ Verifies API key ✓
  ↓ Routes to handle_synthesize

↓ generation_handler.py: handle_synthesize
  ↓ Creates TTSRequest (validates with Pydantic)
  ↓ Calls TTSService.synthesize_streaming

↓ tts_service.py: synthesize_streaming
  ↓ Creates qwen engine (from model_type="qwen")
  ↓ Extracts QwenVoiceConfig parameters
  ↓ voice_id is available from config
  ↓ Calls engine.synthesize_streaming

↓ qwen_tts.py: synthesize_streaming
  ↓ Checks if voice_name in PREDEFINED_VOICES
  ↓ Gets voice_description from PREDEFINED_VOICES
  ↓ Creates voice_prompt (cached)
  ↓ Generates audio with clone_model

✓ SUCCESS
```

#### Path 2: Plain Text Request (Current: BROKEN for Qwen)
```
Client sends plain text: "Hello"

↓ zmq_server.py: _handle_request
  ↓ JSON parsing fails
  ↓ Creates hardcoded request:
      voice_config: { voice_id: "solar", exaggeration: 0.15, ... }
      model_type: NOT SET
  ↓ Routes to handle_synthesize

↓ generation_handler.py: handle_synthesize
  ↓ Creates TTSRequest
  ↓ voice_config becomes ChatterboxVoiceConfig (has exaggeration)
  ↓ model_type is None → uses CONFIG.tts_model

↓ tts_service.py: synthesize_streaming
  ↓ model_type = CONFIG.tts_model (could be "qwen")
  ↓ Creates qwen engine
  ↓ BUT voice_config is ChatterboxVoiceConfig
  ↓ Doesn't match isinstance check
  ↓ Parameters not properly extracted

↓ qwen_tts.py: synthesize_streaming
  ↓ voice_id="solar" is present
  ↓ voice_description is NOT present
  ↓ voice_reference is NOT present
  ↓ voice_name is NOT present
  ↓ None of the if branches match!

❌ FAILURE: ValueError raised
```

---

## Recommendations

### Immediate Fixes (Required)

1. **Fix Missing Union Import**
   - File: `src/tts_inference/models/schemas.py`
   - Add: `from typing import Optional, Literal, Union`

2. **Fix Plain Text Handler for Qwen Compatibility**
   - File: `src/tts_inference/server/zmq_server.py`
   - Option A: Remove plain text handler (enforce JSON)
   - Option B: Make it model-aware:
     ```python
     if CONFIG.tts_model == "qwen":
         request_dict = {
             "text": text,
             "voice_mode": "default",
             "model_type": "qwen",
             "voice_config": {
                 "voice_name": "solar",
                 "speed": 1.0
             }
         }
     else:
         # Current chatterbox config
     ```

### Recommended Improvements

3. **Add Voice ID Validation in Qwen**
   - File: `src/tts_inference/tts/qwen_tts.py`
   - Add a branch to handle voice_id alone (look it up in cache or fail gracefully)

4. **Improve Voice Selection Error Messages**
   - Make the ValueError message more helpful with examples of valid configurations

5. **Document Model-Specific Voice Configurations**
   - Create clear documentation showing:
     - Chatterbox: requires voice_id OR voice_name
     - Qwen: requires voice_id+description OR voice_name (predefined) OR voice_description

6. **Add Integration Tests**
   - Test plain text with both engines
   - Test voice selection paths for qwen
   - Test config type mismatches

---

## Non-Issues (Working as Intended)

- Emotion map and emotional prosody (excluded per request)
- Speed parameter warning for Qwen (documented limitation)
- Voice cache TTL and management (working correctly)
- ZMQ message routing (correct ROUTER/DEALER pattern)
- Audio encoding pipeline (PCM/WAV/Vorbis all correct)

---

## Testing Checklist

- [ ] Plain text request with qwen model
- [ ] JSON request with QwenVoiceConfig and predefined voices
- [ ] JSON request with QwenVoiceConfig and voice_description
- [ ] JSON request with QwenVoiceConfig and voice cloning
- [ ] Mixed model_type + wrong voice_config type
- [ ] Voice cache persistence and invalidation
- [ ] All three audio formats (PCM, WAV, Vorbis) with qwen
