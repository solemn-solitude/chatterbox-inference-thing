# Qwen3-TTS Finetuning Research

**Date:** 2026-01-23  
**Status:** Research Phase  
**Goal:** Improve Qwen3-TTS emotional quality by finetuning on high-quality Chatterbox outputs

---

## Problem Statement

After fixing parameter issues (x_vector_only, subtalker parameters), Qwen3-TTS still produces:
- Very fast, unnatural speech
- Poor emotional quality compared to ChatterboxTTS
- Lacks the "soul" that Chatterbox has

**Current Tradeoff:**
- **ChatterboxTTS:** Excellent quality, emotional depth, but NO streaming support
- **Qwen3-TTS:** Streaming support, fast generation, but poor emotional quality

**Proposed Solution:** Finetune Qwen3-TTS on Chatterbox-generated emotional voice samples

---

## Package Analysis

### Qwen-TTS Package Structure

```
qwen_tts/
├── inference/
│   ├── qwen3_tts_model.py      # Inference wrapper (no training code)
│   └── qwen3_tts_tokenizer.py
├── core/
│   ├── models/
│   │   ├── modeling_qwen3_tts.py         # Core model (Qwen3TTSForConditionalGeneration)
│   │   ├── configuration_qwen3_tts.py    # Model config
│   │   └── processing_qwen3_tts.py       # Processor
│   ├── tokenizer_25hz/                    # 25Hz tokenizer (older)
│   └── tokenizer_12hz/                    # 12Hz tokenizer (current)
└── cli/
    └── demo.py                            # Demo script
```

### Key Findings

1. **HuggingFace Integration:** Uses `transformers.PretrainedConfig`, meaning standard HuggingFace finetuning should work
2. **No Built-in Training:** Package is inference-only wrapper
3. **Model Architecture:** `Qwen3TTSForConditionalGeneration` (similar to transformer sequence-to-sequence models)
4. **Supports LoRA/PEFT:** Since it's a HuggingFace model, PEFT (LoRA, QLoRA) should be compatible

---

## Finetuning Approaches

### Option 1: HuggingFace Trainer (Standard Approach)

**Pros:**
- Well-documented, battle-tested
- Built-in features (checkpointing, logging, distributed training)
- Direct HuggingFace integration

**Cons:**
- Requires custom dataset preparation
- May need to write custom collator for audio data
- More setup work

**Requirements:**
- Training data: `(text, reference_audio, target_audio)` triplets
- Custom data collator for TTS format
- Loss function (likely built into model)

### Option 2: PEFT/LoRA (Parameter-Efficient Finetuning)

**Pros:**
- Much faster training
- Lower memory requirements
- Can train on consumer GPU (24GB VRAM)
- Easier to experiment with different emotional styles
- Can maintain multiple LoRA adapters (one per emotion/style)

**Cons:**
- May have slightly lower quality than full finetuning
- Requires PEFT library (already in dependencies!)

**Strategy:**
```python
from peft import get_peft_model, LoraConfig, TaskType

# Apply LoRA to Qwen model
peft_config = LoraConfig(
    task_type=TaskType.SEQ_2_SEQ_LM,
    inference_mode=False,
    r=8,  # LoRA rank
    lora_alpha=32,
    lora_dropout=0.1,
    target_modules=["q_proj", "v_proj", "k_proj", "o_proj"]  # Attention layers
)

model = get_peft_model(qwen_model.model, peft_config)
```

### Option 3: Voice Prompt Finetuning (Lightweight)

**Idea:** Instead of finetuning the entire model, train only the voice prompt generation

**Pros:**
- Smallest scope
- Fastest training
- Minimal compute

**Cons:**
- May not fix core prosody issues
- Limited impact on emotional quality

---

## Data Generation Strategy

### Leveraging Existing Infrastructure

You already have:
1. **Prompt Template Database:** 100 emotional prompts with target coordinates
2. **Anchor Generator:** System to batch-generate Chatterbox samples
3. **Acoustic Feature Extraction:** Tools to analyze generated audio

### Proposed Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│ Phase 1: Generate Chatterbox Training Dataset              │
└─────────────────────────────────────────────────────────────┘

1. Use existing anchor_generator.py with ChatterboxTTS
2. Generate 100+ high-quality emotional samples
3. Store (text, reference_audio, chatterbox_output_audio) triplets
4. Include acoustic features for validation

┌─────────────────────────────────────────────────────────────┐
│ Phase 2: Prepare Finetuning Data                           │
└─────────────────────────────────────────────────────────────┘

5. Create HuggingFace Dataset with:
   - text: prompt text
   - reference_audio: base voice clip (peaches4)
   - target_audio: Chatterbox emotional output
   - emotion_coords: (valence, arousal, tension, stability)

6. Split into train/val sets (80/20)

┌─────────────────────────────────────────────────────────────┐
│ Phase 3: Finetune Qwen with LoRA                           │
└─────────────────────────────────────────────────────────────┘

7. Apply LoRA to Qwen3TTSForConditionalGeneration
8. Train to match Chatterbox outputs
9. Validate on held-out emotional samples
10. Compare quality: base Qwen vs finetuned Qwen vs Chatterbox
```

### Data Format

```python
# Training sample structure
{
    "text": "Hey there, good boy. How have you been doing today?",
    "reference_audio": np.ndarray,  # Base voice (peaches4)
    "target_audio": np.ndarray,     # Chatterbox emotional output
    "emotion_label": "affectionate_warm",
    "emotion_coords": {
        "valence": 0.7,
        "arousal": 0.5,
        "tension": 0.2,
        "stability": 0.9
    },
    "generation_params": {
        "exaggeration": 0.15,
        "cfg_weight": 0.8,
        "temperature": 0.8
    }
}
```

---

## Technical Requirements

### Compute Resources

**Minimum for LoRA Finetuning:**
- GPU: NVIDIA RTX 3090/4090 (24GB VRAM) or better
- RAM: 32GB+ system RAM
- Storage: 50GB+ for model + dataset

**YOUR HARDWARE: 2x RTX 3090 Ti (24GB VRAM each)**
- ✅ **EXCELLENT** - Exceeds minimum requirements!
- ✅ **24GB VRAM per GPU** - Perfect for LoRA finetuning
- ✅ **Dual GPU Setup** - Can use distributed training for 2x faster training
- ✅ **Can train larger batches** or run experiments in parallel

**Estimated Training Time (with your hardware):**

| Dataset Size | Single GPU | Dual GPU (Distributed) |
|--------------|-----------|------------------------|
| 100 samples | 30-90 min | 15-45 min |
| 500 samples | 1.5-3 hours | 45-90 min |
| 1000 samples | 3-6 hours | 1.5-3 hours |
| 2000 samples | 6-12 hours | 3-6 hours |

- Full finetuning (non-LoRA): 4-12 hours (single GPU) or 2-6 hours (distributed)
- Can also run inference on one GPU while training on the other

**Recommendation:** Start with 100 for validation, scale to 500-1000 for production

**Advantages of Your Dual-GPU Setup:**
1. **Faster Training:** Use both GPUs with `accelerate` for distributed training
2. **Parallel Experiments:** Train multiple LoRA adapters simultaneously
3. **Concurrent Operations:** Keep Qwen inference running on GPU 0 while finetuning on GPU 1
4. **Larger Batch Sizes:** More memory = better gradient estimates

### Software Stack

```toml
# Already in pyproject.toml
peft = ">=0.18.0"  # ✓ Already installed

# Additional requirements
transformers = ">=4.36.0"  # For latest HF features
accelerate = ">=0.25.0"    # For distributed training
datasets = ">=2.16.0"      # For dataset management
wandb = ">=0.16.0"         # (Optional) For experiment tracking
```

### Code Structure

```
docs/
  └── QWEN_FINETUNING_RESEARCH.md  # This document

finetuning/
  ├── __init__.py
  ├── data_generator.py             # Generate Chatterbox training data
  ├── dataset_builder.py            # Build HuggingFace Dataset
  ├── train.py                      # Main training script
  ├── config.py                     # Training configuration
  └── evaluate.py                   # Evaluation scripts

training_data/
  ├── chatterbox_samples/           # Generated audio
  │   ├── sample_001.wav
  │   ├── sample_002.wav
  │   └── ...
  ├── metadata.json                 # Dataset metadata
  └── dataset/                      # HF Dataset cache
```

---

## Implementation Phases

### Phase 1: Data Generation (UPDATED: Recommended 500-1000 samples)

**Strategy: Iterative Generation**

- [x] Existing prompt templates (100 emotional prompts)
- [ ] **Generate additional prompts via LLM** (target: 400-900 more)
- [ ] Modify anchor_generator to save training triplets
- [ ] Generate Chatterbox samples in batches
- [ ] Create metadata file with emotion labels and parameters
- [ ] Validate dataset quality and diversity

**Estimated Time:**
- 100 samples: 2-3 hours
- 500 samples: 8-12 hours
- 1000 samples: 16-24 hours

**Recommended Approach:**
1. Start with 100 samples (use existing templates)
2. Train quick LoRA to validate approach (45 min)
3. If promising, generate 400-900 more samples
4. Retrain on full dataset

**Prompt Generation Pipeline (Semi-Automated):**
```
LLM generates variations
  ↓
Human reviews (optional)
  ↓
Add to prompt_templates table
  ↓
Batch generate with Chatterbox
  ↓
Extract metadata
  ↓
Add to training dataset
```

**Output:** 500-1000 (text, ref_audio, target_audio) triplets

### Phase 2: Dataset Preparation (Estimated: 4-8 hours)

- [ ] Create HuggingFace Dataset class
- [ ] Implement data collator for TTS format
- [ ] Write preprocessing pipeline
- [ ] Split train/validation sets
- [ ] Test data loading

**Output:** Ready-to-train HuggingFace Dataset

### Phase 3: Training Setup (Estimated: 4-8 hours)

- [ ] Research Qwen3TTS model internals
- [ ] Identify trainable parameters
- [ ] Configure LoRA setup
- [ ] Write training script with HF Trainer
- [ ] Set up logging and checkpointing
- [ ] Configure evaluation metrics

**Output:** Working training pipeline

### Phase 4: Finetuning (Estimated: 1-4 hours GPU time)

- [ ] Run initial training experiment
- [ ] Monitor loss curves
- [ ] Validate on held-out samples
- [ ] Tune hyperparameters if needed
- [ ] Train final model

**Output:** Finetuned Qwen3-TTS checkpoint

### Phase 5: Evaluation (Estimated: 2-4 hours)

- [ ] A/B comparison: base Qwen vs finetuned Qwen vs Chatterbox
- [ ] Acoustic feature analysis
- [ ] Subjective quality assessment
- [ ] Measure inference speed impact
- [ ] Document findings

**Output:** Quality metrics and decision point

---

## Risks and Mitigation

### Risk 1: Model Architecture Not Suitable for Finetuning

**Mitigation:**
- Start with LoRA (less invasive)
- Research Qwen3TTS architecture thoroughly
- Have fallback plan (use Chatterbox for quality, Qwen for speed)

### Risk 2: Insufficient Training Data

**IMPORTANT: 100 samples is MINIMUM, not optimal!**

**Recommended Dataset Sizes by Goal:**

| Dataset Size | Training Time* | Expected Quality | Use Case |
|--------------|---------------|------------------|----------|
| 100 samples | 15-45 min | Proof-of-concept | Initial viability test |
| 200-300 samples | 30-90 min | Good improvement | Solid baseline |
| 500-1000 samples | 1-3 hours | Strong results | Production quality |
| 1000-2000 samples | 2-6 hours | Excellent coverage | Maximum quality |

*With your dual-GPU setup

**Given Your Automated Pipeline:**

Since you can easily generate more data (LLM → TTS → metadata), **RECOMMEND 500-1000 samples**:

✅ **Better emotional coverage** across the 4D space (valence, arousal, tension, stability)  
✅ **More text diversity** = better generalization  
✅ **Reduces overfitting** risk  
✅ **Parameter variations** = more robust model  
✅ **Still trains in 1-3 hours** with your hardware  

**Mitigation Strategy:**
1. **Phase 1:** Generate 100 samples, train quick LoRA (45 min)
2. **Evaluate:** If promising, generate 400 more samples (total 500)
3. **Phase 2:** Retrain on full 500-sample dataset (1-2 hours)
4. **Optional:** If quality still lacking, expand to 1000+ samples

### Risk 3: Overfitting to Chatterbox Style

**Mitigation:**
- Proper train/val split
- Early stopping based on validation loss
- Regularization (LoRA dropout, weight decay)

### Risk 4: Quality Improvement Not Worth Effort

**Mitigation:**
- Rapid prototyping with LoRA (1-2 days)
- Quick evaluation before committing to full training
- Clear quality benchmarks from start

---

## Alternative: Hybrid Approach

If finetuning doesn't work well, consider:

1. **Use Chatterbox for "quality mode"** (when latency acceptable)
2. **Use Qwen for "speed mode"** (when streaming required)
3. **Let user or application choose per-request**

```python
# API endpoint
POST /tts/synthesize
{
    "text": "...",
    "quality_mode": "high",  # "high" = Chatterbox, "fast" = Qwen
    "streaming": false
}
```

---

## Next Steps

### Immediate Actions

1. **Research Qwen3-TTS HuggingFace page:**
   - Check for official finetuning examples
   - Review model card for training details
   - Look for community finetuning projects

2. **Inspect Model Internals:**
   ```bash
   # Examine model structure
   python -c "
   from qwen_tts import Qwen3TTSModel
   model = Qwen3TTSModel.from_pretrained('Qwen/Qwen3-TTS-12Hz-1.7B-Base')
   print(model.model)  # Print architecture
   "
   ```

3. **Create Data Generation Script:**
   - Modify `anchor_generator.py` to save training format
   - Generate 10-20 test samples
   - Validate data format

4. **Prototype LoRA Setup:**
   - Quick experiment with PEFT on small sample
   - Verify training loop works
   - Estimate resource requirements

### Decision Point

After initial prototyping (1-2 days):
- **GO:** If training works, quality improves → proceed to full finetuning
- **NO-GO:** If technical blockers or no improvement → use hybrid approach

---

## Resources

### HuggingFace Qwen3-TTS Models

- Base: `Qwen/Qwen3-TTS-12Hz-1.7B-Base`
- VoiceDesign: `Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign`  
- CustomVoice: `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice`

### Documentation to Review

- [ ] Qwen3-TTS Model Card: https://huggingface.co/Qwen/Qwen3-TTS-12Hz-1.7B-Base
- [ ] PEFT Documentation: https://huggingface.co/docs/peft
- [ ] HF Trainer Guide: https://huggingface.co/docs/transformers/training
- [ ] TTS Finetuning Examples: Search HuggingFace for similar projects

### Community Resources

- [ ] Check GitHub for Qwen3-TTS finetuning scripts
- [ ] Search HuggingFace Hub for finetuned Qwen3-TTS models
- [ ] Review papers on prosody transfer in TTS

---

## Conclusion

**Finetuning is feasible** given:
1. ✅ HuggingFace-compatible model
2. ✅ PEFT/LoRA support (lightweight training)
3. ✅ Existing data generation infrastructure (anchor_generator)
4. ✅ High-quality reference (Chatterbox outputs)
5. ✅ Clear evaluation criteria (emotional quality)

**Recommended Path:**
1. Generate 100-200 Chatterbox training samples (use existing infrastructure)
2. Prototype LoRA finetuning on small subset
3. Evaluate quality improvement
4. Decision: proceed with full training or revert to hybrid approach

**Timeline Estimate:** 3-7 days for full pipeline (if pursuing)

**Fallback:** Hybrid mode selection (Chatterbox for quality, Qwen for speed)

---

**Status:** Ready to proceed with data generation prototype
