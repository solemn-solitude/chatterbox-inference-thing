"""OmniVoice TTS engine implementation."""

import asyncio
import logging
import tempfile
from collections.abc import AsyncIterator
from datetime import datetime
from pathlib import Path
from textwrap import dedent

import numpy as np
import torch

from omnivoice import OmniVoice

from tts_inference.tts.base_tts import BaseTTSEngine
from tts_inference.utils.audio_utils import encode_wav_complete

logger = logging.getLogger(__name__)


class OmniVoiceTTSEngine(BaseTTSEngine):
    """OmniVoice TTS engine — voice cloning, voice design, 600+ language support."""

    def __init__(self, inactivity_timeout: int = 600, keep_warm: bool = False):
        self.model: OmniVoice | None = None
        self.device = (
            "cuda" if torch.cuda.is_available()
            else "mps" if torch.backends.mps.is_available()
            else "cpu"
        )
        self._default_sr: int = 24000

        self.inactivity_timeout = inactivity_timeout
        self.keep_warm = keep_warm
        self.last_activity_time: datetime | None = None
        self._monitor_task: asyncio.Task | None = None
        self._is_offloaded = False

    async def initialize(self):
        logger.info(dedent(f"""
        Loading OmniVoice model on {self.device}...
        =================================="""))
        try:
            dtype = torch.float16 if self.device != "cpu" else torch.float32
            loop = asyncio.get_event_loop()
            self.model = await loop.run_in_executor(
                None,
                lambda: OmniVoice.from_pretrained(
                    "k2-fsa/OmniVoice", device_map=self.device, dtype=dtype
                )
            )
            self._default_sr = getattr(self.model, "sampling_rate", 24000)

            logger.info(dedent(f"""
        OmniVoice model loaded successfully
        Sample rate: {self._default_sr} Hz
        =================================="""))

            self.last_activity_time = datetime.now()
            self._is_offloaded = False

            if not self.keep_warm:
                self._start_inactivity_monitor()
            else:
                logger.info("Keep-warm mode enabled, model will remain loaded")

        except Exception as e:
            logger.error("Failed to load OmniVoice model: {}".format(e))
            raise

    @property
    def sample_rate(self) -> int:
        return self._default_sr

    def is_loaded(self) -> bool:
        return self.model is not None and not self._is_offloaded

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

        logger.info("Offloading OmniVoice model from memory...")
        try:
            if self.model is not None:
                del self.model
                self.model = None

            if self.device == "cuda" and torch.cuda.is_available():
                torch.cuda.empty_cache()

            self._is_offloaded = True
            logger.info("OmniVoice model offloaded")
        except Exception as e:
            logger.error(f"Error during model offloading: {e}", exc_info=True)
            raise

    async def _ensure_loaded(self):
        if self._is_offloaded or self.model is None:
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
        language: str | None = None,
        num_step: int = 50,
        guidance_scale: float = 1.0,
        **model_params
    ) -> AsyncIterator[tuple[np.ndarray, int]]:
        await self._ensure_loaded()

        output_sr = sample_rate or self._default_sr
        temp_file = None

        try:
            ref_audio_path = None
            if voice_reference is not None:
                wav_data = encode_wav_complete(voice_reference, self._default_sr)
                temp_file = tempfile.NamedTemporaryFile(mode="wb", suffix=".wav", delete=False)
                temp_file.write(wav_data)
                temp_file.close()
                ref_audio_path = temp_file.name
                logger.info(f"Voice cloning: saved reference audio to {ref_audio_path}")

            if not self.model:
                raise RuntimeError("OmniVoice model is not loaded")

            loop = asyncio.get_event_loop()
            model = self.model
            audios = await loop.run_in_executor(
                None,
                lambda: model.generate(
                    text=text,
                    language=language,
                    ref_audio=ref_audio_path,
                    ref_text=voice_transcript,
                    instruct=voice_description,
                    num_step=num_step,
                    guidance_scale=guidance_scale,
                    speed=speed,
                )
            )

            audio_array = audios[0]
            if isinstance(audio_array, torch.Tensor):
                audio_array = audio_array.cpu().numpy()
            else:
                audio_array = np.asarray(audio_array)

            if audio_array.ndim > 1:
                audio_array = audio_array.flatten()

            if audio_array.dtype != np.float32:
                audio_array = audio_array.astype(np.float32)

            chunk_size = output_sr
            for i in range(0, len(audio_array), chunk_size):
                yield audio_array[i:i + chunk_size], output_sr

        finally:
            if temp_file is not None:
                Path(temp_file.name).unlink(missing_ok=True)
