# TTS System Analysis - Corrected After Review

## Analysis Date
January 23, 2026

## Actual System Design (Corrected Understanding)

### Voice System
- Voices are stored in SQLite database with `voice_id` as primary key
- Audio files (WAV) stored in filesystem, referenced by DB
- `voice_id` is the ONLY identifier used - `voice_name` is NOT used
- NO predefined voices - all voices come from DB
- Voice prompts are cached for performance (3-5x faster subsequent generations)

### Message Format
- Other services in the ZMQ network use **msgpack**
- Current plain text handler was just a proof of concept
- Should switch to msgpack with deserializable dataclasses

### Qwen3-TTS Voice Design
The Qwen model has two approaches:
1. **VoiceDesign model** - Uses `instruct` parameter with voice description to generate reference audio
2. **Direct cloning** - Uses reference audio file directly (x-vector only mode)

The `voice_description` IS used by the actual Qwen VoiceDesign model API (`generate_voice_design(instruct=voice_description)`).

**Question for user:** Should we support VoiceDesign (description-based) or only use direct audio cloning from DB?

---

## Critical Issues (CORRECTED)

### 1. **Wrong Union Type Import Style** ⚠️ HIGH PRIORITY
**Location:** `src/tts_inference/models/schemas.py`

**Problem:**
Per `.clinerules/1-styleguide.md`, should use native union types (3.10+), not `typing.Union`.

Current (WRONG):
```python
voice_config: Union[ChatterboxVoiceConfig, QwenVoiceConfig]
```

Should be:
```python
voice_config: ChatterboxVoiceConfig | QwenVoiceConfig
```

**Impact:** Violates project styleguide, uses deprecated typing module syntax.

**Fix:** Replace all `Union`, `Optional`, `List`, `Dict` with native types:
- `Union[A, B]` → `A | B`
- `Optional[X]` → `X | None`
- `List[X]` → `list[X]`
- `Dict[K, V]` → `dict[K, V]`

---

### 2. **No msgpack Support in ZMQ Handler** ⚠️ HIGH PRIORITY
**Location:** `src/tts_inference/server/zmq_server.py:131-167`

**Problem:**
Currently uses JSON or plain text. Other services use msgpack. Plain text handler is just a POC.

**Required Changes:**
1. Add msgpack deserialization
2. Create proper request dataclass for msgpack payloads
3. Remove plain text POC handler

**Impact:** Cannot communicate with rest of ZMQ network properly.

---

### 3. **No "Get Current Model" Endpoint** ⚠️ HIGH PRIORITY
**Location:** Missing functionality

**Problem:**
Clients need to query which model is currently loaded (qwen vs chatterbox) to know which schema to send.

**Required Workflow:**
```
Client: "What model is loaded?"
Server: {"model": "qwen"}
Client: "OK, sending qwen-format request"
```

**Implementation Needed:**
- Add handler in `zmq_routes/utility_handler.py`
- Return `CONFIG.tts_model`
- Add to request routing

---

### 4. **PREDEFINED_VOICES Should Be Removed** ⚠️ HIGH PRIORITY
**Location:** `src/tts_inference/tts/qwen_tts.py:14-18` and `qwen_tts.py:256-268`

**Problem:**
This is a hallucination. System uses DB-stored voices only.

**What exists:**
```python
PREDEFINED_VOICES: Dict[str, str] = {
    "solar": "Young male voice...",  # Also WRONG - solar is female with semi-deep voice
    "default": "Natural speaking voice..."
}
```

**Required:** Remove entirely. All voices must be looked up in database by voice_id.

---

### 5. **voice_name Field is Unused** ⚠️ MEDIUM PRIORITY
**Locations:**
- `src/tts_inference/models/schemas.py:23` - BaseVoiceConfig
- All TTS engine signatures
- `tts_service.py:71` - passes voice_name but it's not used

**Problem:** The field exists but is never actually used. Only `voice_id` matters.

**Required:** Search and remove all voice_name references if confirmed unused.

---

### 6. **Voice Selection Logic Must Use DB** ⚠️ HIGH PRIORITY
**Location:** `src/tts_inference/tts/qwen_tts.py:229-280`

**Current (WRONG):**
Complex branching with predefined voices, descriptions, etc.

**Should Be:**
```python
# 1. Get voice_id from request
# 2. Load voice audio from DB via VoiceService
# 3. Check cache for this voice_id
# 4. If not cached, create prompt from audio + cache it
# 5. Use cached prompt for generation
```

**Simplified Flow:**
```python
async def synthesize_streaming(self, text, voice_id, ...):
    # Load from DB
    voice_audio = await voice_service.load_voice_reference(voice_id)
    if voice_audio is None:
        raise ValueError(f"Voice not found in DB: {voice_id}")
    
    # Get or create cached prompt
    voice_prompt = await self._ensure_voice_prompt(
        voice_id=voice_id,
        reference_audio=voice_audio
    )
    
    # Generate
    wavs, sr = self.clone_model.generate_voice_clone(
        text=text,
        language=language,
        voice_clone_prompt=voice_prompt,
        **gen_kwargs
    )
```

---

### 7. **Speed Parameter Not Supported** ℹ️ INFO
**Location:** Both `chatterbox_tts.py` and `qwen_tts.py`

**User Feedback:** Speed isn't supported by either model. Chatterbox uses manual audio stretching which affects pitch. May make streaming harder.

**Recommendation:** Remove speed parameter entirely from both engines, or document it won't work for qwen.

---

### 8. **voice_mode Validation Mismatch** ⚠️ LOW PRIORITY
**Location:** `src/tts_inference/models/schemas.py:70-73`

**Problem:**
Validates that clone mode requires voice_id, but doesn't match actual qwen workflow.

For qwen, you ALWAYS need voice_id (to lookup in DB). The voice_mode distinction isn't really meaningful.

**Recommendation:** Simplify - just require voice_id always for qwen.

---

## Required Architecture Changes

### Msgpack Integration

**Add to zmq_server.py:**
```python
import msgpack

async def _handle_request(self, identity_frames: list, request_data: bytes):
    try:
        # Try msgpack first
        try:
            request_dict = msgpack.unpackb(request_data, raw=False)
        except Exception:
            # Fall back to JSON for compatibility
            request_dict = json.loads(request_data.decode('utf-8'))
        
        # ... rest of handling
    except Exception as e:
        logger.error(f"Error handling request: {e}", exc_info=True)
        await self._send_error(identity_frames, str(e))
```

**Add model query handler:**
```python
# In utility_handler.py
async def handle_model_info(identity_frames: list, send_message):
    """Return current model type."""
    from ...utils.config import CONFIG
    
    info = {
        "model": CONFIG.tts_model,
        "sample_rate": get_tts_engine().sample_rate if get_tts_engine().is_loaded() else None
    }
    await send_message(identity_frames, b"response", msgpack.packb(info))
```

### Qwen Voice Workflow Simplification

**New qwen_tts.py synthesize_streaming:**
```python
async def synthesize_streaming(
    self,
    text: str,
    voice_id: str,  # REQUIRED - lookup in DB
    language: str = "Auto",
    sample_rate: int | None = None,
    max_new_tokens: int = 2048,
    top_p: float = 1.0,
    top_k: int = 50,
    temperature: float = 0.9,
    repetition_penalty: float = 1.05,
    voice_reference: np.ndarray | None = None,  # Pre-loaded by service layer
    **model_params
) -> AsyncIterator[tuple[np.ndarray, int]]:
    """Generate speech with streaming.
    
    Args:
        text: Text to synthesize
        voice_id: Voice ID (for caching)
        voice_reference: Pre-loaded voice audio from DB
        ... other params
    """
    if not self.is_loaded():
        await self.initialize()
    
    if voice_reference is None:
        raise ValueError("voice_reference is required (loaded from DB)")
    
    output_sr = sample_rate or self._default_sr
    
    # Get or create cached prompt
    voice_prompt = await self._ensure_voice_prompt(
        voice_id=voice_id,
        reference_audio=voice_reference,
        ref_text=""  # Can be empty for x-vector mode
    )
    
    # Generate
    gen_kwargs = {
        "max_new_tokens": max_new_tokens,
        "top_p": top_p,
        "top_k": top_k,
        "temperature": temperature,
        "repetition_penalty": repetition_penalty,
    }
    
    wavs, sr = self.clone_model.generate_voice_clone(
        text=text,
        language=language,
        voice_clone_prompt=voice_prompt,
        **gen_kwargs
    )
    
    # Stream chunks
    chunk_size = output_sr
    for wav in wavs:
        if isinstance(wav, torch.Tensor):
            wav = wav.cpu().numpy()
        
        if len(wav.shape) > 1:
            wav = wav.flatten()
        if wav.dtype != np.float32:
            wav = wav.astype(np.float32)
        
        for i in range(0, len(wav), chunk_size):
            chunk = wav[i:i + chunk_size]
            yield chunk, output_sr
```

---

## Database Schema (Current - CORRECT)

From `database.py`, the voices table:
```sql
CREATE TABLE IF NOT EXISTS voices (
    voice_id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    sample_rate INTEGER NOT NULL,
    duration_seconds REAL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

This is correct - voices are identified by `voice_id`, files stored in filesystem.

---

## Questions for User

1. **VoiceDesign vs Direct Cloning:** Should we keep the VoiceDesign workflow (using voice_description/instruct parameter)? Or only support direct audio cloning from DB files?

2. **Speed Parameter:** Remove entirely from both engines, or keep with warning?

3. **voice_mode Field:** Keep "default" vs "clone" distinction, or simplify since qwen always uses cloning?

4. **Msgpack Schemas:** Should we create specific msgpack dataclasses, or reuse the Pydantic models with msgpack serialization?

---

## Implementation Checklist

- [ ] Fix Union types to use native `|` syntax
- [ ] Remove Optional, List, Dict from typing imports
- [ ] Add msgpack support to ZMQ handler
- [ ] Add "get current model" query endpoint
- [ ] Remove PREDEFINED_VOICES dict and all references
- [ ] Remove voice_name field (verify not used first)
- [ ] Simplify qwen voice selection to DB-only lookup
- [ ] Update flow: load from DB → check cache → generate
- [ ] Add proper error when voice_id not in DB
- [ ] Test msgpack serialization/deserialization
- [ ] Document the msgpack message schemas
- [ ] Consider removing speed parameter
- [ ] Fix "solar" voice description if we keep VoiceDesign
