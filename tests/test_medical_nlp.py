import csv
import unittest
from pathlib import Path

from modules.medical_nlp import extract_medical_info

SAMPLES = Path(__file__).parent.parent / "data" / "medical_samples.csv"


class TestExtractMedicalInfo(unittest.TestCase):
    def test_fever(self):
        self.assertEqual(extract_medical_info("I have fever")["symptoms"], ["fever"])

    def test_headache(self):
        self.assertEqual(extract_medical_info("My head hurts a lot")["symptoms"], ["headache"])

    def test_durations(self):
        cases = {
            "fever for 2 days": "2 days",
            "fever for two days": "2 days",
            "cough for three days": "3 days",
            "cold since one week": "1 week",
            "cold for a week": "1 week",
            "headache for 2 weeks": "2 weeks",
            "nausea for several days": "several days",
            "dizzy since yesterday": "since yesterday",
            "vomiting today": "today",
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(extract_medical_info(text)["duration"], expected)

    def test_multiple_symptoms(self):
        r = extract_medical_info("I have cough, cold and loose motions with nausea and I feel dizzy")
        self.assertEqual(set(r["symptoms"]), {"cough", "cold", "diarrhea", "nausea", "dizziness"})

    def test_generic_pain_only_without_specific_pain(self):
        self.assertEqual(extract_medical_info("I have pain in my leg")["symptoms"], ["pain"])
        self.assertEqual(extract_medical_info("chest pain")["symptoms"], ["chest pain"])

    def test_negation(self):
        self.assertEqual(extract_medical_info("I have no fever but I am vomiting")["symptoms"], ["vomiting"])

    def test_no_medical_information(self):
        r = extract_medical_info("Hello, I would like to book an appointment")
        self.assertEqual((r["symptoms"], r["duration"], r["supported"]), ([], None, True))

    def test_unsupported_language(self):
        r = extract_medical_info("నాకు జ్వరం ఉంది", "te")
        self.assertEqual((r["symptoms"], r["duration"], r["supported"]), ([], None, False))

    def test_dataset_english_text(self):
        # Runs the English rules on each row's English text. For non-English rows that text is an
        # unvalidated development translation, so this tests the rules, not translation quality.
        with open(SAMPLES, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                with self.subTest(id=row["id"]):
                    r = extract_medical_info(row["expected_english"])
                    self.assertEqual(set(r["symptoms"]), set(row["expected_symptoms"].split(";")))
                    self.assertEqual(r["duration"], row["expected_duration"])


if __name__ == "__main__":
    unittest.main()
