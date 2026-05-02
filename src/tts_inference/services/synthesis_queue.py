"""Single-consumer synthesis queue — serialises all TTS engine calls."""

import asyncio
import logging
from dataclasses import dataclass, field

import numpy as np

from ..tts import get_tts_engine

logger = logging.getLogger(__name__)

_SENTINEL = object()


@dataclass
class _SynthesisJob:
    params: dict
    result_queue: asyncio.Queue = field(default_factory=asyncio.Queue)


class SynthesisQueue:
    def __init__(self, max_depth: int = 10):
        self._queue: asyncio.Queue[_SynthesisJob] = asyncio.Queue(maxsize=max_depth)
        self._consumer_task: asyncio.Task | None = None

    def start(self):
        self._consumer_task = asyncio.create_task(self._consume())
        logger.info("Synthesis queue consumer started")

    async def stop(self):
        if self._consumer_task:
            self._consumer_task.cancel()
            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass
        logger.info("Synthesis queue consumer stopped")

    @property
    def depth(self) -> int:
        return self._queue.qsize()

    async def _consume(self):
        while True:
            job = await self._queue.get()
            try:
                engine = get_tts_engine()
                await engine.initialize()
                async for chunk, sr in engine.synthesize_streaming(**job.params):
                    await job.result_queue.put((chunk, sr))
            except Exception as e:
                await job.result_queue.put(e)
            finally:
                await job.result_queue.put(_SENTINEL)
                self._queue.task_done()

    async def submit(self, params: dict):
        """Submit a synthesis job and yield audio chunks as they are produced.

        Raises RuntimeError immediately if the queue is full.
        """
        job = _SynthesisJob(params=params)
        try:
            self._queue.put_nowait(job)
        except asyncio.QueueFull:
            raise RuntimeError(
                f"Synthesis queue is full — {self._queue.maxsize} jobs already pending"
            )

        logger.debug(f"Job submitted, queue depth now {self.depth}")

        while True:
            item = await job.result_queue.get()
            if item is _SENTINEL:
                return
            if isinstance(item, Exception):
                raise item
            yield item


class _QueueHolder:
    _instance: SynthesisQueue | None = None

    @classmethod
    def get(cls) -> SynthesisQueue:
        if cls._instance is None:
            cls._instance = SynthesisQueue()
            cls._instance.start()
        return cls._instance

    @classmethod
    async def stop(cls):
        if cls._instance is not None:
            await cls._instance.stop()
            cls._instance = None


def get_synthesis_queue() -> SynthesisQueue:
    return _QueueHolder.get()


async def stop_synthesis_queue():
    await _QueueHolder.stop()
