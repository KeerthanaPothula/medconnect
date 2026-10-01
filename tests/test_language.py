import csv
import unittest
from pathlib import Path

from modules.language import detect_language

SAMPLES = Path(__file__).parent.parent / "data" / "medical_samples.csv"


class TestDetectLanguage(unittest.TestCase):
    def test_english(self):
        self.assertEqual(detect_language("I have had a bad headache since yesterday")["code"], "en")

    def test_telugu(self):
        r = detect_language("నాకు రెండు రోజులుగా తలనొప్పి ఉంది")
        self.assertEqual((r["code"], r["name"]), ("te", "Telugu"))

    def test_hindi(self):
        self.assertEqual(detect_language("मुझे तीन दिन से बुखार है")["code"], "hi")

    def test_kannada(self):
        self.assertEqual(detect_language("ನನಗೆ ಜ್ವರ ಇದೆ")["code"], "kn")

    def test_empty_input(self):
        for text in ("", "   ", None):
            r = detect_language(text)
            self.assertIsNone(r["code"])
            self.assertIn("empty", r["name"])

    def test_short_input_is_uncertain(self):
        # langdetect alone would call this Danish with 99.99% confidence
        self.assertIn("too short", detect_language("fever 2 days")["name"])

    def test_no_language_features(self):
        self.assertIsNone(detect_language("123 456 !!!")["code"])

    def test_unsupported_language(self):
        r = detect_language("मला तीन दिवसांपासून ताप आहे")  # Marathi
        self.assertIsNone(r["code"])

    def test_dataset_languages(self):
        with open(SAMPLES, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                with self.subTest(id=row["id"]):
                    self.assertEqual(detect_language(row["patient_text"])["code"], row["language"])


if __name__ == "__main__":
    unittest.main()
