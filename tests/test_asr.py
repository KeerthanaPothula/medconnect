"""ASR unit tests. Whisper is mocked (_load/_transcribe), so nothing is downloaded.
The real-model check lives in test_asr_real.py."""
import io
import unittest
import wave
from unittest.mock import patch

import numpy as np

from modules import asr
from modules.asr import transcribe_audio


def make_wav(seconds=1.0, rate=16000, channels=1, amplitude=0.5, sampwidth=2):
    """In-memory WAV with a 440 Hz tone (amplitude 0 = silence)."""
    t = np.arange(int(seconds * rate)) / rate
    tone = (amplitude * np.sin(2 * np.pi * 440 * t) * 32767).astype("<i2")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(sampwidth)
        w.setframerate(rate)
        frames = np.repeat(tone, channels).tobytes()
        w.writeframes(frames if sampwidth == 2 else (tone // 256 + 128).astype("u1").tobytes())
    return buf.getvalue()


class TestInputValidation(unittest.TestCase):
    """None of these may touch the model."""

    def setUp(self):
        p = patch.object(asr, "_load", side_effect=AssertionError("model must not load"))
        p.start()
        self.addCleanup(p.stop)

    def check(self, audio, error):
        r = transcribe_audio(audio)
        self.assertEqual(r, {"success": False, "text": None, "language": None, "error": error})

    def test_no_audio(self):
        self.check(None, asr.NO_AUDIO)
        self.check(b"", asr.NO_AUDIO)
        self.check(io.BytesIO(b""), asr.NO_AUDIO)

    def test_invalid_audio(self):
        self.check(b"this is not a wav file", asr.INVALID_AUDIO)
        self.check(make_wav()[:30], asr.INVALID_AUDIO)  # truncated header
        self.check(make_wav(sampwidth=1), asr.INVALID_AUDIO)  # 8-bit PCM unsupported
        self.check(12345, asr.INVALID_AUDIO)

    def test_silent_or_too_short(self):
        self.check(make_wav(amplitude=0), asr.SILENT_AUDIO)
        self.check(make_wav(seconds=0.1), asr.SILENT_AUDIO)


class TestDecode(unittest.TestCase):
    def test_resamples_stereo_44k_to_mono_16k(self):
        samples = asr._decode_wav(make_wav(seconds=2, rate=44100, channels=2))
        self.assertEqual(samples.dtype, np.float32)
        self.assertEqual(len(samples), 32000)
        self.assertAlmostEqual(float(np.abs(samples).max()), 0.5, places=2)


@patch.object(asr, "_load", return_value=object())
class TestTranscription(unittest.TestCase):
    def test_success(self, load):
        with patch.object(asr, "_transcribe", return_value=("I have had a headache for two days.", "en")) as tr:
            r = transcribe_audio(io.BytesIO(make_wav()))  # file-like, like st.audio_input's UploadedFile
        self.assertEqual(r, {"success": True, "text": "I have had a headache for two days.", "language": "en", "error": None})
        samples, language = tr.call_args.args[1:]
        self.assertEqual((len(samples), language), (16000, None))

    def test_forced_language_is_passed_through(self, load):
        with patch.object(asr, "_transcribe", return_value=("నాకు జ్వరం ఉంది", "te")) as tr:
            r = transcribe_audio(make_wav(), language="te")
        self.assertEqual(tr.call_args.args[2], "te")
        self.assertEqual((r["text"], r["language"]), ("నాకు జ్వరం ఉంది", "te"))

    def test_transcription_error(self, load):
        with patch.object(asr, "_transcribe", side_effect=RuntimeError("boom")), self.assertLogs(asr.log):
            r = transcribe_audio(make_wav())
        self.assertEqual((r["success"], r["text"], r["error"]), (False, None, asr.TRANSCRIPTION_FAILED))

    def test_no_speech_recognised(self, load):
        with patch.object(asr, "_transcribe", return_value=("", "en")):
            r = transcribe_audio(make_wav())
        self.assertEqual((r["success"], r["error"]), (False, asr.NO_SPEECH))


class TestModelUnavailable(unittest.TestCase):
    def test_load_failure(self):
        with patch.object(asr, "_load", side_effect=OSError("no network")), self.assertLogs(asr.log):
            r = transcribe_audio(make_wav())
        self.assertEqual((r["success"], r["text"], r["error"]), (False, None, asr.MODEL_UNAVAILABLE))


if __name__ == "__main__":
    unittest.main()
