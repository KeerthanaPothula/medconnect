"""Local speech-to-text with OpenAI Whisper (open weights), run on this machine via Hugging Face transformers.

No external or paid speech API is used: audio never leaves the machine. The model
(openai/whisper-small, ~0.97 GB) is downloaded once on first use into models/ and loaded once per process.

Input is WAV audio (what Streamlit's st.audio_input records), decoded with the stdlib `wave` module,
so no ffmpeg is needed. Returns structured results and never raises.
"""
import functools
import io
import logging
import wave
from pathlib import Path

import numpy as np

log = logging.getLogger(__name__)

MODEL = "openai/whisper-small"
MODEL_DIR = Path(__file__).resolve().parent.parent / "models"
SAMPLE_RATE = 16000  # Whisper expects 16 kHz mono
MIN_SECONDS = 0.3
SILENCE_LEVEL = 0.01  # peak amplitude (of 1.0) below which a recording is treated as silent

NO_AUDIO = "No audio recorded."
INVALID_AUDIO = "The recording could not be read. Please record again."
SILENT_AUDIO = "The recording is empty or silent. Please record again and speak clearly."
MODEL_UNAVAILABLE = "Speech recognition model unavailable."
TRANSCRIPTION_FAILED = "Transcription failed."
NO_SPEECH = "No speech was recognised in the recording."


def _decode_wav(data):
    """WAV bytes -> float32 mono samples at 16 kHz in [-1, 1]. Raises ValueError/wave.Error/EOFError if invalid."""
    with wave.open(io.BytesIO(data)) as w:
        if w.getsampwidth() != 2:
            raise ValueError("only 16-bit PCM WAV is supported")
        rate, channels = w.getframerate(), w.getnchannels()
        samples = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float32) / 32768
    samples = samples.reshape(-1, channels).mean(axis=1)
    if rate != SAMPLE_RATE:
        # ponytail: linear-interpolation resampling; fine for speech, use a proper resampler if audio quality matters.
        n = int(len(samples) * SAMPLE_RATE / rate)
        samples = np.interp(np.linspace(0, len(samples) - 1, n), np.arange(len(samples)), samples).astype(np.float32)
    return samples


@functools.lru_cache(maxsize=None)  # load once per process; failures are not cached, so a retry can succeed
def _load():
    import torch  # heavy imports only when voice input is actually used
    from transformers import WhisperForConditionalGeneration, WhisperProcessor

    processor = WhisperProcessor.from_pretrained(MODEL, cache_dir=MODEL_DIR)
    model = WhisperForConditionalGeneration.from_pretrained(MODEL, cache_dir=MODEL_DIR)
    model.eval()
    return processor, model, torch


def _transcribe(bundle, samples, language):
    """Return (text, language code). language=None lets Whisper detect it."""
    processor, model, torch = bundle
    # ponytail: Whisper's input window is 30 s, longer audio is cut off; use chunked long-form decoding if needed.
    inputs = processor(samples, sampling_rate=SAMPLE_RATE, return_tensors="pt", return_attention_mask=True)
    with torch.no_grad():
        if language is None:
            token = processor.tokenizer.decode(model.detect_language(inputs.input_features)[0])  # e.g. "<|te|>"
            language = token.strip("<|>")
        ids = model.generate(inputs.input_features, attention_mask=inputs.attention_mask,
                             language=language, task="transcribe")
    return processor.batch_decode(ids, skip_special_tokens=True)[0].strip(), language


def transcribe_audio(audio_data, language=None):
    """Transcribe WAV audio (bytes or a file-like object such as st.audio_input's result).

    language: optional ISO code to force (e.g. "te"); None = Whisper detects the language.
    Returns {"success", "text", "language", "error"}. "language" is Whisper's own guess
    (most likely language, no confidence score) or the forced code.
    """
    result = {"success": False, "text": None, "language": None, "error": None}
    if audio_data is None:
        return {**result, "error": NO_AUDIO}
    data = audio_data.getvalue() if hasattr(audio_data, "getvalue") else audio_data
    if not isinstance(data, (bytes, bytearray)) or not data:
        return {**result, "error": NO_AUDIO if not data else INVALID_AUDIO}
    try:
        samples = _decode_wav(bytes(data))
    except (wave.Error, EOFError, ValueError):
        return {**result, "error": INVALID_AUDIO}
    if len(samples) < MIN_SECONDS * SAMPLE_RATE or np.abs(samples).max() < SILENCE_LEVEL:
        return {**result, "error": SILENT_AUDIO}

    try:
        bundle = _load()
    except Exception:
        log.exception("Loading Whisper failed")
        return {**result, "error": MODEL_UNAVAILABLE}
    try:
        text, detected = _transcribe(bundle, samples, language)
    except Exception:
        log.exception("Transcription failed")
        return {**result, "error": TRANSCRIPTION_FAILED}
    if not text:
        return {**result, "language": detected, "error": NO_SPEECH}
    return {**result, "success": True, "text": text, "language": detected}
