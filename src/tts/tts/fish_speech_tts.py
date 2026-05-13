"""FishSpeech TTS engine implementation."""

import asyncio
import io
import logging
from collections.abc import AsyncIterator
from datetime import datetime
from textwrap import dedent

import numpy as np
import torch

from fish_speech.inference_engine import TTSInferenceEngine
from fish_speech.models.text2semantic.inference import launch_thread_safe_queue
from fish_speech.models.dac.inference import load_model as load_decoder_model
from fish_speech.utils.schema import ServeReferenceAudio, ServeTTSRequest

from tts.tts.base_tts import BaseTTSEngine
from tts.utils.audio_utils import encode_wav_complete
from tts.utils.config import CONFIG

logger = logging.getLogger(__name__)


class FishSpeechTTSEngine(BaseTTSEngine):
    engine_name = "fish-speech"
    engine_params = [
        {"name": "temperature",        "type": "float", "label": "Temperature",        "min": 0.0, "max": 2.0,        "step": 0.05, "default": 0.7},
        {"name": "top_p",              "type": "float", "label": "Top-P",              "min": 0.0, "max": 1.0,        "step": 0.05, "default": 0.7},
        {"name": "repetition_penalty", "type": "float", "label": "Repetition Penalty", "min": 1.0, "max": 2.0,        "step": 0.05, "default": 1.2},
        {"name": "seed",               "type": "int",   "label": "Seed (-1=random)",   "min": -1,  "max": 2147483647, "step": 1,    "default": -1},
    ]

    def __init__(self, inactivity_timeout: int = 600, keep_warm: bool = False):
        self._engine: TTSInferenceEngine | None = None
        self._decoder_model = None
        self._llama_queue = None
        self._default_sr: int = 44100

        self.device = (
            "cuda" if torch.cuda.is_available()
            else "mps" if torch.backends.mps.is_available()
            else "cpu"
        )

        self.inactivity_timeout = inactivity_timeout
        self.keep_warm = keep_warm
        self.last_activity_time: datetime | None = None
        self._monitor_task: asyncio.Task | None = None
        self._is_offloaded = False

    async def initialize(self):
        logger.info(dedent(f"""
        Loading FishSpeech model on {self.device}...
        =================================="""))

        precision = torch.float16 if self.device != "cpu" else torch.float32
        checkpoint_path = CONFIG.fish_speech_checkpoint_path
        decoder_path = CONFIG.fish_speech_decoder_path

        loop = asyncio.get_event_loop()

        self._llama_queue = await loop.run_in_executor(
            None,
            lambda: launch_thread_safe_queue(
                checkpoint_path=checkpoint_path,
                device=self.device,
                precision=precision,
                compile=False,
            ),
        )

        self._decoder_model = await loop.run_in_executor(
            None,
            lambda: load_decoder_model(
                config_name="modded_dac_vq",
                checkpoint_path=decoder_path,
                device=self.device,
            ),
        )

        self._engine = TTSInferenceEngine(
            llama_queue=self._llama_queue,
            decoder_model=self._decoder_model,
            precision=precision,
            compile=False,
        )

        self._default_sr = getattr(self._decoder_model, "sample_rate", 44100)

        logger.info(dedent(f"""
        FishSpeech model loaded successfully
        Sample rate: {self._default_sr} Hz
        =================================="""))

        self.last_activity_time = datetime.now()
        self._is_offloaded = False

        if not self.keep_warm:
            self._start_inactivity_monitor()
        else:
            logger.info("Keep-warm mode enabled, model will remain loaded")

    @property
    def sample_rate(self) -> int:
        return self._default_sr

    def is_loaded(self) -> bool:
        return self._engine is not None and not self._is_offloaded

    def _start_inactivity_monitor(self):
        if self._monitor_task is None or self._monitor_task.done():
            self._monitor_task = asyncio.create_task(self._monitor_inactivity())
            logger.info("Started inactivity monitor (timeout: {}s)".format(self.inactivity_timeout))

    async def _monitor_inactivity(self):
        try:
            while True:
                await asyncio.sleep(60)
                if self.last_activity_time and not self._is_offloaded:
                    inactive = (datetime.now() - self.last_activity_time).total_seconds()
                    if inactive >= self.inactivity_timeout:
                        logger.info(f"Model inactive for {inactive:.0f}s, offloading...")
                        await self.offload_model()
        except asyncio.CancelledError:
            logger.info("Inactivity monitor stopped")
        except Exception as e:
            logger.error(f"Error in inactivity monitor: {e}", exc_info=True)

    async def offload_model(self):
        if self._is_offloaded:
            return

        logger.info("Offloading FishSpeech model from memory...")
        try:
            self._engine = None
            self._llama_queue = None
            self._decoder_model = None

            if self.device == "cuda" and torch.cuda.is_available():
                torch.cuda.empty_cache()

            self._is_offloaded = True
            logger.info("FishSpeech model offloaded")
        except Exception as e:
            logger.error(f"Error during model offloading: {e}", exc_info=True)
            raise

    async def _ensure_loaded(self):
        if self._is_offloaded or self._engine is None:
            logger.info("Model was offloaded, reloading...")
            await self.initialize()
        self.last_activity_time = datetime.now()
        self._is_offloaded = False

    async def synthesize_streaming(
        self,
        text: str,
        voice_id: str | None = None,
        voice_reference: np.ndarray | None = None,
        voice_transcript: str | None = None,
        voice_description: str | None = None,
        speed: float = 1.0,
        sample_rate: int | None = None,
        temperature: float = 0.7,
        top_p: float = 0.7,
        repetition_penalty: float = 1.2,
        chunk_length: int = 200,
        seed: int | None = None,
        normalize: bool = True,
        **model_params,
    ) -> AsyncIterator[tuple[np.ndarray, int]]:
        await self._ensure_loaded()

        output_sr = sample_rate or self._default_sr
        references = []

        if voice_reference is not None:
            wav_bytes = encode_wav_complete(voice_reference, self._default_sr)
            references.append(
                ServeReferenceAudio(audio=wav_bytes, text=voice_transcript or "")
            )

        request = ServeTTSRequest(
            text=text,
            references=references,
            chunk_length=chunk_length,
            format="pcm",
            normalize=normalize,
            seed=seed,
            max_new_tokens=0,
            top_p=top_p,
            repetition_penalty=repetition_penalty,
            temperature=temperature,
            streaming=True,
        )

        loop = asyncio.get_event_loop()

        def _run_inference():
            return list(self._engine.inference(request))

        results = await loop.run_in_executor(None, _run_inference)

        for result in results:
            if result.code == "error":
                raise RuntimeError(f"FishSpeech inference error: {result.error}")
            if result.code != "segment":
                continue

            _, audio_data = result.audio
            if isinstance(audio_data, bytes):
                audio_array = np.frombuffer(audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            else:
                audio_array = np.asarray(audio_data, dtype=np.float32)
                if audio_array.dtype != np.float32 or audio_array.max() > 1.0:
                    audio_array = audio_array.astype(np.float32) / 32768.0

            if audio_array.ndim > 1:
                audio_array = audio_array.flatten()

            if speed != 1.0:
                from scipy import signal as scipy_signal
                new_length = int(len(audio_array) / speed)
                if new_length >= 1:
                    audio_array = scipy_signal.resample(audio_array, new_length).astype(np.float32)

            yield audio_array, output_sr
