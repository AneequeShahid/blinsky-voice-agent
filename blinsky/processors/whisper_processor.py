"""
WhisperProcessor: record audio from mic and transcribe with faster-whisper.
Inspired by pipecat's processor chain pattern — each processor receives
input, transforms it, passes to next.
"""
from __future__ import annotations

import io
import queue
import threading
import time
import wave
from typing import Optional

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel


class WhisperProcessor:
    """Records audio from default microphone and returns transcript text."""

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_duration: float = 3.0,
        model_size: str = "tiny",
    ) -> None:
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_duration = chunk_duration
        self.silence_threshold = 500
        self.silence_duration = 1.2
        self.max_listen_duration = 15.0

        self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
        self._audio_queue: "queue.Queue[np.ndarray]" = queue.Queue()
        self._recording = threading.Event()

    # ------------------------------------------------------------------
    # Recording helpers
    # ------------------------------------------------------------------
    def _audio_callback(
        self, indata: np.ndarray, frames: int, time_info, status
    ) -> None:
        if status:
            print(f"[Whisper] audio status: {status}")
        self._audio_queue.put(indata.copy())

    def record_chunk(self) -> Optional[np.ndarray]:
        """Record a single speech chunk — stops on silence or timelimit."""
        chunk_samples = int(self.sample_rate * self.chunk_duration)
        max_chunks = int(self.max_listen_duration / self.chunk_duration)
        max_silent_chunks = int(self.silence_duration / self.chunk_duration)

        frames: list[np.ndarray] = []
        silent_chunks = 0
        total_chunks = 0

        print("[Whisper] recording...")
        self._recording.set()

        stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="int16",
            blocksize=chunk_samples,
            callback=self._audio_callback,
        )
        stream.start()

        try:
            while total_chunks < max_chunks:
                try:
                    data = self._audio_queue.get(timeout=self.chunk_duration + 1)
                    frames.append(data)
                    total_chunks += 1

                    rms = np.sqrt(np.mean(data.astype(np.float32) ** 2))
                    if rms < self.silence_threshold:
                        silent_chunks += 1
                    else:
                        silent_chunks = 0

                    if silent_chunks >= max_silent_chunks and total_chunks > 2:
                        break
                except queue.Empty:
                    break
        finally:
            stream.stop()
            stream.close()
            self._recording.clear()

        if not frames:
            return None

        audio = np.concatenate(frames, axis=0)
        return audio

    # ------------------------------------------------------------------
    # Transcription
    # ------------------------------------------------------------------
    def transcribe(self, audio: np.ndarray) -> str:
        """Transcribe raw int16 audio array with faster-whisper."""
        if audio is None or len(audio) == 0:
            return ""

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio.tobytes())
        buf.seek(0)

        segments, _info = self.model.transcribe(
            buf,
            beam_size=1,
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=500,
                speech_pad_ms=200,
            ),
        )

        text_parts = [seg.text.strip() for seg in segments]
        return " ".join(text_parts).strip()

    def process(self) -> str:
        """Record and transcribe in one call — returns transcript."""
        audio = self.record_chunk()
        if audio is None:
            return ""
        text = self.transcribe(audio)
        return text
