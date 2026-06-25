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

try:
    import sounddevice as sd
except ImportError:
    sd = None

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None


class WhisperProcessor:
    """Records audio from default microphone and returns transcript text."""

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_duration: float = 0.5,
        model_size: str = "tiny",
    ) -> None:
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_duration = chunk_duration
        self.silence_duration = 2.0        # changed: 1.2 → 2.0s
        self.max_listen_duration = 30.0    # changed: 15.0 → 30.0s

        if WhisperModel is not None:
            self.model = WhisperModel(model_size, device="cpu", compute_type="int8")
        else:
            self.model = None
            print("[Whisper] faster-whisper not installed. Transcription disabled.")
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
        """Record a single speech chunk — stops on silence or timelimit.

        Changes vs original:
        - silence_duration: 2.0s, max_listen_duration: 30.0s
        - Dynamic threshold: calibrate on first 0.5s of audio
        - Minimum speech duration: discard if < 0.5s of non-silent audio
        - Visual progress: prints dots while recording
        """
        chunk_samples = int(self.sample_rate * self.chunk_duration)
        max_chunks = int(self.max_listen_duration / self.chunk_duration)
        max_silent_chunks = int(self.silence_duration / self.chunk_duration)

        # How many chunks make up the calibration window (first 0.5s)
        calibration_duration = 0.5
        calibration_chunks_needed = max(
            1, int(calibration_duration / self.chunk_duration)
        )

        frames: list[np.ndarray] = []
        calibration_frames: list[np.ndarray] = []
        dynamic_threshold: Optional[float] = None
        calibrated = False

        silent_chunks = 0
        total_chunks = 0

        if sd is None:
            print("[Whisper Bypass] sounddevice not installed. Cannot record.")
            return None

        print("[Whisper] Listening", end="", flush=True)  # visual feedback start
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
                    print(".", end="", flush=True)  # visual feedback: dot per chunk

                    rms = np.sqrt(np.mean(data.astype(np.float32) ** 2))

                    # ---- Calibration phase ----
                    if not calibrated:
                        calibration_frames.append(rms)
                        if len(calibration_frames) >= calibration_chunks_needed:
                            ambient_rms = float(np.mean(calibration_frames))
                            dynamic_threshold = max(ambient_rms * 1.5, 200.0)
                            calibrated = True
                        # During calibration we skip silence counting
                        continue

                    # ---- VAD with dynamic threshold ----
                    if rms < dynamic_threshold:
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
            print()  # newline after dots

        if not frames:
            return None

        audio = np.concatenate(frames, axis=0)

        # ---- Minimum speech duration guard ----
        # Recompute threshold for post-processing (fall back to 200 if never calibrated)
        threshold = dynamic_threshold if dynamic_threshold is not None else 200.0
        min_speech_duration = 0.5  # seconds

        # Count non-silent samples by checking frame-level RMS
        speech_samples = 0
        for frame in frames:
            frame_rms = np.sqrt(np.mean(frame.astype(np.float32) ** 2))
            if frame_rms >= threshold:
                speech_samples += frame.shape[0]

        total_speech_duration = speech_samples / self.sample_rate
        if total_speech_duration < min_speech_duration:
            print(
                f"[Whisper] Speech too short ({total_speech_duration:.2f}s < "
                f"{min_speech_duration}s), discarding."
            )
            return None

        return audio

    # ------------------------------------------------------------------
    # Transcription
    # ------------------------------------------------------------------
    def transcribe(self, audio: np.ndarray) -> str:
        """Transcribe raw int16 audio array with faster-whisper."""
        if self.model is None:
            return ""
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
