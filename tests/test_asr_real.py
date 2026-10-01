"""Manual integration test against the real local Whisper model (downloads ~0.97 GB on first run).

Skipped by default. Run with (PowerShell):
    $env:MEDCONNECT_REAL_MODEL = "1"; python -m unittest tests.test_asr_real -v

Transcribes every data/audio/<lang>_*.wav (16-bit PCM WAV, <lang> = en/hi/te/ta/kn) and runs the
transcript through the existing pipeline: language detection -> IndicTrans2 (if not English) -> extraction.
Prints transcripts, Whisper's language guess and timings for manual inspection.
Only synthetic/development recordings belong in data/audio/, never real patient audio.
This is a smoke test, not a transcription-accuracy evaluation.
"""
import os
import time
import unittest
from pathlib import Path

from modules import asr
from modules.asr import transcribe_audio
from modules.language import detect_language
from modules.medical_nlp import extract_medical_info
from modules.translation import translate_to_english

AUDIO_DIR = Path(__file__).parent.parent / "data" / "audio"


@unittest.skipUnless(os.environ.get("MEDCONNECT_REAL_MODEL") == "1", "set MEDCONNECT_REAL_MODEL=1 to run")
class TestRealWhisper(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        t = time.perf_counter()
        asr._load()
        print(f"\nloaded {asr.MODEL} in {time.perf_counter() - t:.1f}s")

    def test_audio_samples_through_pipeline(self):
        files = sorted(AUDIO_DIR.glob("*.wav"))
        self.assertTrue(files, f"no .wav files in {AUDIO_DIR}")
        for path in files:
            with self.subTest(file=path.name):
                t = time.perf_counter()
                r = transcribe_audio(path.read_bytes())
                print(f"\n[{path.name}, {time.perf_counter() - t:.1f}s] whisper language={r['language']}\n  text: {r['text']}")
                self.assertTrue(r["success"], r["error"])
                lang = detect_language(r["text"])["code"] or ("en" if r["text"].isascii() else None)
                english = r["text"] if lang == "en" else translate_to_english(r["text"], lang)["text"]
                info = extract_medical_info(english, "en") if english else None
                print(f"  detect_language={lang} english={english!r}\n  extracted={info}")
                if path.name == "en_headache_two_days.wav":  # synthetic TTS sample, text known
                    self.assertEqual(r["language"], "en")
                    self.assertEqual((info["symptoms"], info["duration"]), (["headache"], "2 days"))


if __name__ == "__main__":
    unittest.main()
