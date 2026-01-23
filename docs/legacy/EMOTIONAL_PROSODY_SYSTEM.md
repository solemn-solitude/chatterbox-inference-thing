# Emotional Prosody Control System for Chatterbox TTS

**Version:** 0.2.0  
**Last Updated:** 2026-01-15  
**Status:** Design & Planning Phase

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [The Problem We're Solving](#the-problem-were-solving)
3. [The Solution: Emotional Voice Atlas](#the-solution-emotional-voice-atlas)
4. [Technical Architecture](#technical-architecture)
5. [Key Components](#key-components)
6. [Implementation Phases](#implementation-phases)
7. [Current Project State](#current-project-state)
8. [Design Decisions & Rationale](#design-decisions--rationale)
9. [References](#references)

---

## Executive Summary

We are building an **emotional prosody control system** for the Chatterbox TTS inference server that allows runtime selection of emotionally appropriate speech synthesis based on conversational context, without retraining the base TTS model.

**Core Concept:** Pre-generate ~100+ voice samples from a neutral cloned voice by driving it with emotionally extreme prompts. Map each sample to coordinates in a 4-dimensional emotional space (Valence, Arousal, Tension, Stability). At runtime, a small LLM analyzes context and outputs target emotional coordinates, and the TTS system selects/interpolates the appropriate pre-generated voice anchor.

**Why This Matters:** TTS models are blind to pragmatic intent. The same text can require vastly different prosody depending on context. By separating emotional reasoning (LLM) from prosodic rendering (TTS), we achieve contextually appropriate, emotionally coherent speech synthesis.

---

## The Problem We're Solving

### Prosodic Ambiguity in TTS

Modern TTS models generate speech from text alone, but lack understanding of:
- **Conversational context** - What was said before?
- **User emotional state** - How is the user feeling?
- **Response intent** - What is the *purpose* of this utterance?

**Example:** The phrase "you are okay" could be:
- **Reassurance after distress** → Warm, slow, low tension
- **Checking physical status** → Neutral, rising intonation
- **Dismissive** → Flat, clipped
- **Consoling grief** → Soft, low energy, stable
- **Playful teasing** → Light, rhythmic

Text alone cannot resolve this. The TTS model will default to neutral or statistically average prosody, which often feels *wrong*.

### Emotional Discontinuity

Even when TTS models have implicit emotional priors, they lack:
- **Temporal coherence** - Emotions can jump erratically between turns
- **Contextual awareness** - No understanding of conversation flow
- **Intent modeling** - Confusing sentiment analysis with response strategy

### Current Limitations

Existing approaches fail because:
- **Emotion from text classifiers** are brittle and context-blind
- **Fine-tuning TTS models** for each user/scenario is impractical
- **Mirroring user emotion** creates unstable, clingy responses
- **Discrete emotion labels** (happy/sad/angry) don't match human reality

---

## The Solution: Emotional Voice Atlas

### Core Idea

We create a **pre-computed emotional manifold** by:

1. **Start with ONE neutral cloned voice** (identity-locked)
2. **Generate emotional boundary samples** by driving TTS with extreme emotional prompts
3. **Extract acoustic features** from each sample (pitch, energy, rate, tension)
4. **Assign coordinates** in 4D emotional space
5. **Store ~100 anchor voices** with their coordinates
6. **At runtime:** LLM outputs target coordinates → System selects/interpolates anchors → Synthesize

### Why This Works

✅ **Exploits existing emotional priors** - ChatterboxTTS already encodes emotion implicitly  
✅ **No retraining required** - Pure sampling and selection  
✅ **Continuous emotional space** - Not discrete labels, but smooth gradients  
✅ **Contextually driven** - LLM has conversation history and user state  
✅ **Emotionally stable** - Can enforce smoothing/hysteresis between turns  
✅ **Debuggable** - Every coordinate maps to a real audio sample  

### Research Validation

This approach aligns with current TTS research:
- **Daisy-TTS** - Prosody decomposition for flexible emotion control
- **Continuous emotional TTS** - Arousal-valence spaces with intensity scaling
- **Hierarchical emotion control** - Fine-grained prosodic manipulation

(See ChatGPT conversation excerpt in References section)

---

## Technical Architecture

### 4-Dimensional Emotional Space

We use **4 orthogonal axes** to represent emotional prosody:

| Axis | Range | Separates | Acoustic Markers |
|------|-------|-----------|------------------|
| **Valence** | -1.0 (negative) → +1.0 (positive) | Sadness vs Joy | Spectral brightness, pitch direction |
| **Arousal** | 0.0 (flat) → 1.0 (intense) | Calm vs Excited | Energy, speaking rate, pitch variance |
| **Tension** | 0.0 (relaxed) → 1.0 (tense) | Joy vs Anger | Jaw tightness, spectral harshness, clipped phrasing |
| **Stability** | 0.0 (irregular) → 1.0 (stable) | Surprise vs Calm | Prosody predictability over time |

**Example Coordinate Mappings:**

```
Sadness:   {valence: -0.7, arousal: 0.2, tension: 0.3, stability: 0.9}
Anger:     {valence: -0.6, arousal: 0.9, tension: 0.95, stability: 0.6}
Joy:       {valence: 0.8, arousal: 0.8, tension: 0.1, stability: 0.85}
Surprise:  {valence: 0.0, arousal: 0.9, tension: 0.7, stability: 0.2}
Neutral:   {valence: 0.0, arousal: 0.5, tension: 0.3, stability: 0.8}
```

### System Flow

```
┌─────────────────┐
│ Conversation    │
│ Context + User  │
│ Emotional State │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Small LLM      │◄─── "What emotional intent is appropriate?"
│  (External)     │     (ground, encourage, reassure, celebrate, etc.)
└────────┬────────┘
         │
         │ Outputs: {valence, arousal, tension, stability}
         ▼
┌─────────────────┐
│ Emotional       │
│ Anchor Selector │◄─── Nearest-neighbor or interpolation
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ TTS Synthesis   │◄─── Uses selected voice anchor(s)
│ with Selected   │
│ Voice Anchor    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Audio Output    │
└─────────────────┘
```

### Data Pipeline

**Phase 1: Anchor Generation (Offline)**
```
Neutral Voice → Emotional Prompts → TTS Generate → Extract Features → Assign Coordinates → Store in DB
```

**Phase 2: Runtime Selection**
```
LLM Coordinates → Query DB → Select/Interpolate Anchors → Load Voice Reference → TTS Synthesize
```

---

## Key Components

### 1. Prompt Template Library & Anchor Generation System

**Purpose:** Define emotional prompts and generate ~100 emotional voice samples

**Prompt Template Requirements:**
- **Length**: ~15 seconds of speech (approximately 40-60 words)
- **Clarity**: Very obvious and unambiguous emotional intent
- **Consistency**: Maintain single emotion throughout the prompt
- **Natural language**: Conversational, not theatrical
- **Pre-tuned parameters**: Each template has optimized generation settings

**Parameter Sweet Spots (Discovered through Testing):**
- **Exaggeration**: `0.1 - 0.3` (sweet spot around `0.15`)
  - Higher values cause speed-up and instability
  - Lower values in this range preserve stability while adding emotional "soul"
- **CFG Weight**: `0.7 - 1.0` (higher is generally better)
  - Brings emotion and "soul" into synthesis
  - Improves adherence to cloned voice characteristics
- **Temperature**: `0.5 - 1.2` (varies by emotion)
- **Repetition Penalty**: `1.0 - 1.5`

**Generation Strategy (Hybrid Approach):**

1. **Core Emotional Templates (50-70 prompts)**
   - Hand-crafted by external LLM (to avoid content restrictions)
   - Each template tagged with:
     - Emotional intent label (for reference)
     - Pre-tuned generation parameters
     - Target emotional coordinates (initial estimate)

2. **Parameter Variations (20-30 anchors)**
   - Slight variations of core templates
   - Adjust temperature, cfg_weight within optimal ranges
   - Creates intensity gradations

3. **Intensity Levels (20-30 anchors)**
   - Same emotion, different intensity via prompt content
   - Examples: mild sadness → moderate sadness → extreme sadness

**Data Flow:**
```
Prompt Templates (stored in DB)
  ↓
Load template + parameters
  ↓
TTS Generation with neutral base voice
  ↓
Save audio file to disk (file path stored in DB, NOT file data)
  ↓
Extract acoustic features
  ↓
Assign/validate emotional coordinates
  ↓
Store anchor metadata in DB
```

**Outputs:**
- ~100-120 WAV files (stored on disk in organized directory structure)
- Prompt templates database (text + parameters)
- Emotional anchors database (metadata + file paths + coordinates)

### 2. Acoustic Feature Extraction

**Purpose:** Extract measurable prosodic features from each generated anchor for validation and quality control

**IMPORTANT:** This is NOT for analyzing user audio/sentiment. Acoustic analysis is used to:
- Validate that generated emotional anchors sound as intended
- Extract quantitative features for coordinate verification
- Provide post-generation quality control

**Features to Extract:**
- **Pitch**: Mean F0, F0 variance, F0 range, F0 contour slope
- **Energy**: RMS energy, dynamic range
- **Temporal**: Speaking rate (phonemes/sec), pause duration, rhythm variance
- **Spectral**: Spectral centroid, spectral tilt, formant clarity
- **Stability**: Coefficient of variation in pitch/energy over time

**Modern Tools (Updated 2026):** 
- **torchaudio** - PyTorch-native audio processing (GPU-accelerated, actively maintained)
- **PyWorld** or **CREPE** - Modern pitch extraction (more accurate than Praat-based tools)
- Custom metrics for emotional validation

**Why These Tools:**
- Active development and maintenance
- Better performance and accuracy
- GPU acceleration support
- Cleaner integration with PyTorch-based TTS models

**Outputs:**
- Feature vector for each anchor
- Validation metrics comparing target vs actual emotional characteristics

### 3. Coordinate Mapping System

**Purpose:** Assign 4D emotional coordinates to each anchor

**Approaches:**
1. **Manual labeling** - Human annotator assigns coordinates
2. **Semi-automatic** - Extract features → Run clustering/dimensionality reduction → Human adjustment
3. **Regression from features** - Train mapping: acoustic features → emotional coordinates

**Initial Phase:** Manual labeling with guided templates
**Future:** Train automatic mapper once we have labeled dataset

**Outputs:**
- Emotional coordinates for each anchor
- Coordinate → Anchor mapping table

### 4. Extended Database Schema

**Purpose:** Store prompt templates and emotional anchor metadata

**New Tables:**

```sql
-- Prompt templates for anchor generation
CREATE TABLE prompt_templates (
    template_id TEXT PRIMARY KEY,
    
    -- The prompt text (~15 seconds of speech, 40-60 words)
    prompt_text TEXT NOT NULL,
    
    -- Metadata for reference
    emotion_label TEXT,              -- Human-readable label (e.g., "comfort_quiet")
    description TEXT,                -- Description of emotional intent
    
    -- Pre-tuned generation parameters (optimal for this specific prompt)
    exaggeration REAL DEFAULT 0.15,  -- Sweet spot: 0.1-0.3
    cfg_weight REAL DEFAULT 0.8,     -- Sweet spot: 0.7-1.0
    temperature REAL DEFAULT 0.8,    -- Varies by emotion
    repetition_penalty REAL DEFAULT 1.2,
    
    -- Target emotional coordinates (initial estimate, refined after generation)
    target_valence REAL,
    target_arousal REAL,
    target_tension REAL,
    target_stability REAL,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Emotional anchor voices (generated from templates)
CREATE TABLE emotional_anchors (
    anchor_id TEXT PRIMARY KEY,
    base_voice_id TEXT NOT NULL,    -- Links to original neutral voice
    template_id TEXT NOT NULL,      -- Links to prompt template used
    
    -- File storage (path only, NOT binary data)
    audio_file_path TEXT NOT NULL,  -- Path to WAV file on disk
    sample_rate INTEGER NOT NULL,
    duration_seconds REAL,
    
    -- ACTUAL emotional coordinates (assigned after generation & analysis)
    valence REAL NOT NULL,          -- -1.0 to 1.0
    arousal REAL NOT NULL,          -- 0.0 to 1.0
    tension REAL NOT NULL,          -- 0.0 to 1.0
    stability REAL NOT NULL,        -- 0.0 to 1.0
    
    -- Extracted acoustic features (for analysis & validation)
    mean_pitch REAL,
    pitch_variance REAL,
    pitch_range REAL,
    mean_energy REAL,
    energy_variance REAL,
    speaking_rate REAL,
    spectral_centroid REAL,
    
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (base_voice_id) REFERENCES voices(voice_id),
    FOREIGN KEY (template_id) REFERENCES prompt_templates(template_id)
);

-- Indexes for fast queries
CREATE INDEX idx_emotional_coords ON emotional_anchors(valence, arousal, tension, stability);
CREATE INDEX idx_base_voice ON emotional_anchors(base_voice_id);
CREATE INDEX idx_template ON emotional_anchors(template_id);
```

**File Storage Organization:**
```
{VOICE_DIR}/
  anchors/
    {base_voice_id}/
      {anchor_id}.wav
      
Example:
  ~/.local/share/tts-inference/
    anchors/
      neutral_companion_v1/
        comfort_quiet_01.wav
        anger_intense_01.wav
        joy_excited_01.wav
        ...
```

**Key Design Principles:**
- ✅ Audio files stored on disk, only paths in database (good practice)
- ✅ Prompt templates separate from anchors (reusable, version-able)
- ✅ Parameters stored with templates (each prompt has optimal settings)
- ✅ Target coords vs actual coords (allows comparison & refinement)

### 5. Anchor Selection/Interpolation Engine

**Purpose:** Select appropriate voice anchor(s) given target coordinates

**Algorithms:**

**A) Nearest Neighbor (Simple)**
```python
def select_anchor(target_coords):
    """Find closest anchor in 4D space using Euclidean distance."""
    return min(anchors, key=lambda a: distance(a.coords, target_coords))
```

**B) K-Nearest Neighbors with Interpolation**
```python
def select_anchors_weighted(target_coords, k=3):
    """Find k nearest anchors and weight by inverse distance."""
    neighbors = get_k_nearest(anchors, target_coords, k)
    weights = [1/distance(n.coords, target_coords) for n in neighbors]
    return neighbors, normalize(weights)
```

**C) Barycentric Interpolation (Advanced)**
- Find simplex (5 points in 4D space) containing target
- Compute barycentric coordinates
- Blend voice embeddings

**Initial Implementation:** Start with A, upgrade to B

### 6. LLM Integration Interface

**Purpose:** Accept emotional coordinates from external LLM orchestrator

**IMPORTANT ARCHITECTURE NOTE:**

This TTS service does NOT host or include an LLM. The emotional decision-making happens in the **external conversation orchestrator** where it belongs. Here's why:

```
User Audio → STT → Text
                     ↓
                  LLM Orchestrator (External - NOT in this app)
                  - Has full conversation context
                  - Understands user emotional state  
                  - Makes pragmatic reasoning
                  - Outputs: response text + emotional coordinates
                     ↓
                  This TTS Service
                  - Receives text + coordinates
                  - Selects appropriate anchor
                  - Synthesizes emotionally appropriate audio
```

**Why This Separation:**
- LLM needs conversation context (history, user state, relationship dynamics)
- TTS shouldn't duplicate emotional reasoning
- Clean separation of concerns: reasoning vs rendering
- Allows different LLM backends without changing TTS
- Reduces complexity and resource requirements

**New API Endpoint:**
```http
POST /tts/synthesize-emotional
Content-Type: application/json
Authorization: Bearer <api-key>

{
  "text": "I understand this is difficult. Take your time.",
  "emotional_coords": {
    "valence": 0.3,    // Slightly positive (supportive)
    "arousal": 0.2,    // Low energy (calm)
    "tension": 0.1,    // Relaxed (comforting)
    "stability": 0.9   // Very stable (grounding)
  },
  "base_voice_id": "companion_voice",
  "audio_format": "pcm",
  "sample_rate": 24000
}
```

**Processing:**
1. Receive text and coordinates from external orchestrator
2. Query emotional_anchors table for nearest match
3. Load selected anchor voice reference
4. Synthesize using `voice_mode="clone"` with selected anchor
5. Stream audio back to orchestrator

**Integration Examples:**

The external orchestrator can use various strategies:
- **LLM-based**: Prompt LLM to output coordinates based on conversation
- **Rule-based**: Simple sentiment → coordinate mapping
- **Hybrid**: Rules + LLM for complex cases
- **Default**: Always use neutral coordinates if no emotion needed

### 7. Emotional Smoothing/Hysteresis

**Purpose:** Prevent erratic emotional jumps between turns

**Implementation:**
```python
class EmotionalStateMachine:
    def __init__(self, max_delta_per_turn=0.3, smoothing_factor=0.5):
        self.current_state = neutral_coords()
        self.max_delta = max_delta_per_turn
        self.smoothing = smoothing_factor
    
    def update(self, target_coords):
        """Apply smoothing and delta limiting."""
        # Interpolate between current and target
        smoothed = lerp(self.current_state, target_coords, self.smoothing)
        
        # Clip maximum change
        delta = smoothed - self.current_state
        if magnitude(delta) > self.max_delta:
            delta = normalize(delta) * self.max_delta
        
        self.current_state += delta
        return self.current_state
```

**Maintains per-conversation session state**

---

## Implementation Phases

### Phase 0: Foundation (Current Session)
- [x] Read and understand ChatGPT conversation
- [x] Explore existing Chatterbox codebase  
- [x] Create this design document
- [x] Create implementation roadmap
- [x] Created emotion taxonomy (100 distinct emotions across 12 categories)
- [x] Generated prompt templates SQL seed data

### Phase 1: Database Extensions ✅ COMPLETE
- [x] Design `emotional_anchors` table schema
- [x] Design `prompt_templates` table schema
- [x] Create database migration system (`migrations.py`, `migrations_definition.py`)
- [x] Extend `VoiceDatabase` class with emotional anchor methods
- [x] Add migration script for existing database
- [x] Create data models (Pydantic schemas) for emotional coordinates
- [x] Create CLI commands for database management (`db migrate`, `db migration-status`, `db seed-templates`)
- [x] Test database operations (migrations applied, 100 templates seeded)

### Phase 2: Prompt Templates & Anchor Generation ✅ COMPLETE
- [x] Create prompt_templates database table
- [x] Import emotional prompts from external LLM
- [x] Validate prompt templates (length, clarity, parameter ranges)
- [x] Create CLI command: `tts-inference anchors generate`
- [x] Implement batch generation system with optimal parameters
- [x] Add progress tracking and logging
- [x] Organize generated files in directory structure
- [x] Create anchor listing tool: `tts-inference anchors list`
- [x] Documentation for generation workflow

### Phase 3: Acoustic Feature Extraction ✅ COMPLETE
- [x] Add acoustic analysis dependencies (torchaudio, librosa, pyworld, crepe, scipy)
- [x] Implement feature extraction module (`acoustic_features.py`)
- [x] Create analysis CLI command (`tts-inference anchors analyze`)
- [x] Extract pitch, energy, temporal, and spectral features
- [x] Add validation against expected emotional characteristics
- [x] Store extracted features in database (`update_emotional_anchor_features` method)

### Phase 4: Coordinate Assignment
- [ ] Create coordinate labeling interface/tool
- [ ] Implement manual labeling workflow
- [ ] Add visualization tools (plot anchors in 2D projections)
- [ ] Validate coordinate assignments
- [ ] Document coordinate assignment guidelines

### Phase 5: Selection & Synthesis
- [ ] Implement nearest-neighbor anchor selection
- [ ] Extend `TTSService` with emotional synthesis path
- [ ] Create new API endpoint: `/tts/synthesize-emotional`
- [ ] Add coordinate validation and bounds checking
- [ ] Integration tests

### Phase 6: Emotional State Management
- [ ] Design session state storage
- [ ] Implement smoothing/hysteresis algorithms
- [ ] Add per-conversation state tracking
- [ ] Create state visualization/debugging tools
- [ ] Test temporal coherence

### Phase 7: Optimization & Production
- [ ] Implement K-NN with interpolation
- [ ] Add anchor preloading/caching
- [ ] Performance profiling and optimization
- [ ] Production deployment checklist
- [ ] Monitoring and metrics

### Phase 8: Research & Iteration
- [ ] Collect user feedback
- [ ] Train automatic coordinate mapper from acoustic features
- [ ] Experiment with advanced interpolation (barycentric)
- [ ] A/B testing framework
- [ ] Publish findings

---

## Current Project State

### Existing Infrastructure (Ready to Build On)

✅ **Voice Management System**
- Upload/store voice references (WAV files)
- SQLite database for voice metadata
- Load voice references for cloning

✅ **TTS Synthesis Pipeline**
- ChatterboxTTS/ChatterboxTurboTTS integration
- Voice cloning support (`audio_prompt_path`)
- Prosody controls: `exaggeration`, `cfg_weight`, `temperature`, `repetition_penalty`
- Streaming and batch synthesis

✅ **API Infrastructure**
- FastAPI server (REST + WebSocket)
- ZMQ server (high-performance messaging)
- Authentication (API keys)
- Client library (HTTP + ZMQ)

✅ **Audio Processing**
- PCM, WAV, Vorbis encoding
- Sample rate handling
- Speed adjustment (resampling)

### What Needs to Be Built

❌ **Emotional anchor storage** - Database schema extension  
❌ **Anchor generation tools** - CLI and batch processing  
❌ **Acoustic analysis** - Feature extraction pipeline  
❌ **Coordinate mapping** - Assignment and validation  
❌ **Emotional synthesis endpoint** - New API route  
❌ **Selection algorithm** - Nearest-neighbor implementation  
❌ **State management** - Smoothing and hysteresis  
❌ **LLM integration** - Example LLM that outputs coordinates  

---

## Design Decisions & Rationale

### Why 4 Axes Instead of 3?

**Arousal + Valence alone cannot separate:**
- Anger vs Sadness (both negative valence, different arousal)
- Joy vs Surprise (both high arousal, different stability)

**Tension** cleanly splits anger (tense) from joy (relaxed).  
**Stability** separates surprise (irregular) from other high-arousal states.

Research supports at least 3 axes (Valence, Arousal, Dominance), we replace Dominance with Tension + Stability for better acoustic mapping.

### Why Pre-Generation Instead of Real-Time Control?

**Advantages:**
- Deterministic, reproducible
- No risk of model drift
- Can validate each anchor
- Fast runtime (just load reference)
- Works with ANY TTS that supports voice cloning

**Disadvantages:**
- Storage cost (~100 x 5-10sec = 5-50MB WAV files)
- Limited resolution (discrete anchors, not continuous)

**Mitigation:** Interpolation between anchors provides continuity

### Why Numeric Coordinates Instead of Emotion Labels?

**Labels create problems:**
- Mode collapse ("assistant always sounds 'warm'")
- Anthropomorphic reasoning errors in LLM
- No intensity scaling
- Cultural/linguistic bias

**Numbers force honesty:**
- LLM must reason about specific axes
- Smooth interpolation possible
- Debuggable (plot coordinates over conversation)
- Language-agnostic

### Why External LLM Instead of Integrated?

**Separation of concerns:**
- Emotional reasoning requires large context window, world knowledge
- TTS requires GPU for model inference
- Different scaling characteristics
- LLM can be swapped/upgraded independently

**Could integrate later**, but decoupled architecture is more flexible.

---

## References

### Original ChatGPT Conversation

**Key Insights from GPT-5:**

> "What you're really proposing is learning an emotion-conditioned prosody manifold learned indirectly via self-distillation. That's a real thing people half-do in research, just usually messier."

> "You're not just 'nudging tone'. You're doing prosodic disambiguation... Your LLM can resolve this because it knows: What was said before, User emotional state, Relationship dynamics, Recent emotional statistics."

> "This is essentially cross-modal grounding: LLM has theory of mind, TTS has no theory of mind. You're letting the LLM lend that understanding to TTS. This is the correct division of labor."

**Research Mentioned:**
- **Daisy-TTS** - Prosody decomposition with explicit emotion control
- **Continuous emotional TTS** - Arousal-valence space with intensity scaling
- **Hierarchical emotion control** - Multi-level prosodic manipulation

### Current Research Alignment

Our approach is **validated by current TTS research** which shows:
✅ Emotional prosody can be represented in continuous, navigable space  
✅ Conditioning synthesis on emotional coordinates improves naturalness  
✅ Learned latent spaces outperform discrete emotion labels  

We're essentially building a **practical implementation** of research concepts using voice cloning as the control mechanism.

---

## Document Maintenance

**Update this document when:**
- Starting a new session (add progress notes)
- Making architectural decisions (document rationale)
- Discovering new insights (add to references)
- Completing implementation phases (mark checkboxes)

**Version History:**
- `0.1.0` (2026-01-15) - Initial design document created
- `0.2.0` (2026-01-15) - Added parameter sweet spots, prompt template database schema, file storage strategy
- `0.2.1` (2026-01-15) - Completed Phase 0: emotion taxonomy and prompt templates

---

## Session Notes

### Session 2026-01-15 (Evening)

**Accomplishments:**

1. **Emotion Taxonomy Development**
   - Created comprehensive list of 100 distinct emotions across 12 categories
   - Removed redundant synonyms (e.g., ecstatic/jubilant/elated)
   - Added missing fundamental emotions (disgust, contempt, shame, guilt, boredom, jealousy)
   - Included nuanced states: energy levels (energized, exhausted, sleepy), social dynamics (defensive, condescending, sarcastic), power dynamics (defiant, protective, assertive)
   - Balanced coverage across positive (35), neutral (15), negative (41), and complex (9) states

2. **Prompt Template Generation**
   - Created 100 hand-crafted conversational prompts (40-60 words each, ~10-15 seconds speech)
   - Each prompt demonstrates unambiguous emotional intent with natural, non-theatrical language
   - Assigned optimized generation parameters per emotion:
     - Exaggeration: 0.05-0.28 (varying by intensity)
     - CFG weight: 0.7-1.0 (emotion-dependent)
     - Temperature: 0.5-1.2 (tuned for stability vs. expression)
     - Repetition penalty: 1.2-1.3 (consistent)
   - Mapped each prompt to target 4D emotional coordinates (valence, arousal, tension, stability)
   - Generated SQL seed data: `src/tts_inference/emotion_map/prompt_templates_seed.sql`
   - Verified SQLite compatibility (100 rows successfully inserted and queried)

3. **Design Refinements**
   - Confirmed emotion-to-coordinate mapping strategy
   - Documented prompt requirements and best practices
   - Established file organization: emotion map stored in `src/tts_inference/emotion_map/`

3. **Phase 1: Database Extensions** ✅ COMPLETE
   - Created database migration system (`migrations.py`, `migrations_definition.py`)
   - Defined `prompt_templates` and `emotional_anchors` table schemas
   - Extended `VoiceDatabase` class with comprehensive methods for:
     - Prompt template management
     - Emotional anchor CRUD operations
     - K-NN search in 4D emotional space (using SQLite)
   - Created Pydantic schemas:
     - `EmotionalCoordinates` with distance calculation
     - `PromptTemplate`, `EmotionalAnchor` 
     - `EmotionalTTSRequest` for API integration
   - Built CLI commands:
     - `tts-inference db migrate` - Run migrations
     - `tts-inference db migration-status` - Show history
     - `tts-inference db seed-templates` - Load 100 templates
   - Successfully tested: 3 migrations applied, 100 templates seeded

4. **Architectural Clarifications**
   - **Acoustic Analysis Purpose**: Clarified this is for OUTPUT validation, NOT user audio analysis
   - **Modern Tool Stack**: Upgraded from librosa/parselmouth to torchaudio/PyWorld (2026 best practices)
   - **LLM Integration**: Documented external orchestrator architecture - LLM lives OUTSIDE this app
   - **Data Flow**: One neutral voice → 100 emotional variations → Runtime k-NN selection
   - **Separation of Concerns**: TTS handles rendering, external LLM handles emotional reasoning

**Next Steps:**
- Phase 2: Build anchor generation CLI tool (`generate-anchors` command)
- Implement batch generation system with progress tracking
- Generate actual voice anchors from neutral base voice using prompt templates
- Add acoustic feature extraction (torchaudio + PyWorld)

**Files Created:**
- `emotions_to_convey.txt` - Emotion taxonomy reference
- `src/tts_inference/emotion_map/prompt_templates_seed.sql` - Database seed data (100 prompts)
- `src/tts_inference/models/migrations.py` - Migration framework
- `src/tts_inference/emotion_map/migrations_definition.py` - Migration definitions
- `src/tts_inference/emotion_map/__init__.py` - Module initialization
- Updated: `src/tts_inference/models/database.py` - Added emotional anchor methods
- Updated: `src/tts_inference/models/schemas.py` - Added emotional prosody schemas
- Updated: `src/tts_inference/cli.py` - Added database management commands

**Database State:**
- Version: 3 (all migrations applied)
- Tables: `voices`, `prompt_templates`, `emotional_anchors`, `schema_migrations`
- Data: 100 prompt templates seeded and ready for anchor generation

---

**End of Document**
