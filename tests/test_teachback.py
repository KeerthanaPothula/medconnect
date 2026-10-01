import csv
import unittest
from pathlib import Path
from unittest.mock import patch

from modules import translation
from modules.teachback import NEEDS_CLARIFICATION, UNCERTAIN, UNDERSTOOD, verify_teachback
from modules.translation import translate_from_english, translate_to_english

DATASET = Path(__file__).parent.parent / "data" / "teachback_dataset.csv"
AFTER_FOOD = "Take the medicine after food."


class TestVerifyTeachback(unittest.TestCase):
    def test_correct_understanding(self):
        r = verify_teachback(AFTER_FOOD, "I will take the medicine after eating.")
        self.assertEqual(r["status"], UNDERSTOOD)
        self.assertEqual(r["score"], 1.0)
        self.assertEqual(set(r["matched_concepts"]), {"take the medicine", "after food"})
        self.assertEqual((r["missing_concepts"], r["contradictions"]), ([], []))

    def test_paraphrases_from_real_model_output(self):
        # Phrasings IndicTrans2 actually produced for Telugu teach-back replies.
        self.assertEqual(verify_teachback(AFTER_FOOD, "I take the medicine after a meal.")["status"], UNDERSTOOD)
        self.assertEqual(verify_teachback(AFTER_FOOD, "I take the medicine before meals.")["status"], NEEDS_CLARIFICATION)

    def test_incorrect_timing(self):
        r = verify_teachback(AFTER_FOOD, "I will take the medicine before food.")
        self.assertEqual(r["status"], NEEDS_CLARIFICATION)
        self.assertEqual(r["missing_concepts"], ["after food"])
        self.assertIn("before food", r["feedback"])

    def test_missing_concept(self):
        r = verify_teachback(AFTER_FOOD, "Okay, I will take the medicine.")
        self.assertEqual(r["status"], NEEDS_CLARIFICATION)
        self.assertEqual((r["missing_concepts"], r["score"]), (["after food"], 0.5))
        self.assertIn("after food", r["feedback"])

    def test_unrelated_response(self):
        r = verify_teachback(AFTER_FOOD, "I will go to college tomorrow.")
        self.assertEqual((r["status"], r["score"], r["matched_concepts"]), (UNCERTAIN, 0.0, []))

    def test_negated_response(self):
        r = verify_teachback(AFTER_FOOD, "I will not take the medicine after food.")
        self.assertEqual(r["status"], NEEDS_CLARIFICATION)
        self.assertIn("take the medicine", r["missing_concepts"])
        self.assertIn("would not", r["feedback"])

    def test_negation_in_instruction_is_not_expected(self):
        r = verify_teachback("Take the medicine after food, not before food.", "I take the medicine after eating.")
        self.assertEqual(r["status"], UNDERSTOOD)

    def test_numbers_words_and_frequency_conflict(self):
        r = verify_teachback("Take two tablets twice a day for 5 days.", "I take 2 tablets three times a day for five days.")
        self.assertEqual(r["status"], NEEDS_CLARIFICATION)
        self.assertEqual(r["missing_concepts"], ["twice a day"])
        self.assertIn("three times a day", r["feedback"])

    def test_instruction_without_known_concepts(self):
        r = verify_teachback("Hello, how are you?", "I am fine.")
        self.assertEqual((r["status"], r["score"]), (UNCERTAIN, None))

    def test_development_dataset(self):
        # 12 synthetic development rows (not an evaluation set); every label must be reproduced.
        with open(DATASET, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                with self.subTest(id=row["id"]):
                    self.assertEqual(verify_teachback(row["instruction"], row["patient_response"])["status"],
                                     row["expected_label"])


@patch.object(translation, "_load", return_value=object())
class TestMultilingualTeachback(unittest.TestCase):
    def test_telugu_round_trip(self, load):
        # English instruction -> Telugu -> patient replies in Telugu -> English -> verification.
        # Model outputs are fakes; only the wiring is tested here.
        with patch.object(translation, "_generate", return_value=["<telugu instruction>"]) as gen:
            shown = translate_from_english(AFTER_FOOD, "te")
        self.assertEqual(gen.call_args.args[2:], ("eng_Latn", "tel_Telu"))
        self.assertTrue(shown["success"])
        with patch.object(translation, "_generate", return_value=["I will take the medicine after eating."]) as gen:
            back = translate_to_english("<telugu response>", "te")
        self.assertEqual(gen.call_args.args[2:], ("tel_Telu", "eng_Latn"))
        self.assertEqual(verify_teachback(AFTER_FOOD, back["text"])["status"], UNDERSTOOD)


if __name__ == "__main__":
    unittest.main()
