"""Manual integration test against the real IndicTrans2 models (downloads ~1.8 GB on first run).

Skipped by default. Run with (PowerShell):
    $env:MEDCONNECT_REAL_MODEL = "1"; python -m unittest tests.test_translation_real -v
Requires `hf auth login` with access to the two gated ai4bharat models (see README).

It checks that real translations come back in the right script and that the English rules find the
expected symptoms in the model's English output. It prints every translation, the extraction result,
and load/translation times for manual inspection.
It is a smoke test on a few synthetic rows, not a translation-quality evaluation.
"""
import csv
import os
import re
import time
import unittest
from pathlib import Path

from modules import translation
from modules.medical_nlp import extract_medical_info
from modules.translation import translate_from_english, translate_to_english

SAMPLES = Path(__file__).parent.parent / "data" / "medical_samples.csv"
SCRIPTS = {"hi": r"[ऀ-ॿ]", "te": r"[ఀ-౿]", "ta": r"[஀-௿]", "kn": r"[ಀ-೿]"}


def timed(fn, *args):
    t = time.perf_counter()
    out = fn(*args)
    return out, time.perf_counter() - t


@unittest.skipUnless(os.environ.get("MEDCONNECT_REAL_MODEL") == "1", "set MEDCONNECT_REAL_MODEL=1 to run")
class TestRealModel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for direction in ("to_en", "from_en"):  # download (first run only) + load, timed separately from translation
            _, secs = timed(translation._load, direction)
            print(f"\nloaded {translation.MODELS[direction]} in {secs:.1f}s")

    def test_dataset_to_english_then_extract(self):
        with open(SAMPLES, encoding="utf-8") as f:
            rows = [r for r in csv.DictReader(f) if r["language"] != "en"]
        for row in rows:
            with self.subTest(id=row["id"], lang=row["language"]):
                r, secs = timed(translate_to_english, row["patient_text"], row["language"])
                print(f"\n[{row['language']}->en, {secs:.1f}s] {row['patient_text']}\n  -> {r['text']}")
                self.assertTrue(r["success"], r["error"])
                info = extract_medical_info(r["text"], "en")
                print(f"  extracted: {info['symptoms']} | {info['duration']}")
                self.assertEqual(set(info["symptoms"]), set(row["expected_symptoms"].split(";")))

    def test_instruction_to_each_language(self):
        for code, script in SCRIPTS.items():
            with self.subTest(lang=code):
                r, secs = timed(translate_from_english, "Take the medicine after food.", code)
                print(f"\n[en->{code}, {secs:.1f}s] {r['text']}")
                self.assertTrue(r["success"], r["error"])
                self.assertRegex(r["text"], script)
                self.assertIsNone(re.search(r"[A-Za-z]{4,}", r["text"]), "output still contains English words")


if __name__ == "__main__":
    unittest.main()
