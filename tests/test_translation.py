"""Translation unit tests. The model is mocked (_load/_generate), so nothing is downloaded.
The real-model check lives in test_translation_real.py."""
import unittest
from unittest.mock import patch

from modules import translation
from modules.medical_nlp import extract_medical_info
from modules.translation import translate_from_english, translate_to_english

FAKE_BUNDLE = object()


def fake_generate(output):
    return patch.object(translation, "_generate", return_value=[output])


@patch.object(translation, "_load", return_value=FAKE_BUNDLE)
class TestTranslation(unittest.TestCase):
    def test_english_input_bypasses_model(self, load):
        r = translate_to_english("I have fever", "en")
        self.assertEqual((r["success"], r["text"], r["error"]), (True, "I have fever", None))
        load.assert_not_called()

    def test_indic_to_english_paths(self, load):
        for code, tag in [("te", "tel_Telu"), ("hi", "hin_Deva"), ("kn", "kan_Knda"), ("ta", "tam_Taml")]:
            with self.subTest(code=code), fake_generate("I have fever.") as gen:
                r = translate_to_english("ఏదో వాక్యం", code)
                self.assertEqual(r, {"success": True, "text": "I have fever.", "source_language": code,
                                     "target_language": "en", "error": None})
                load.assert_called_with("to_en")
                self.assertEqual(gen.call_args.args[2:], (tag, "eng_Latn"))

    def test_english_to_indic_path(self, load):
        with fake_generate("<model output>") as gen:
            r = translate_from_english("Take the medicine after food.", "te")
        self.assertTrue(r["success"])
        load.assert_called_with("from_en")
        self.assertEqual(gen.call_args.args[2:], ("eng_Latn", "tel_Telu"))

    def test_sentences_are_split(self, load):
        with fake_generate("x") as gen:
            translate_to_english("पहला वाक्य। दूसरा वाक्य।", "hi")
        self.assertEqual(gen.call_args.args[1], ["पहला वाक्य।", "दूसरा वाक्य।"])

    def test_empty_and_malformed_input(self, load):
        for text in ("", "   ", None, 123):
            r = translate_to_english(text, "te")
            self.assertFalse(r["success"])
            self.assertIsNone(r["text"])
        load.assert_not_called()

    def test_unsupported_language(self, load):
        for r in (translate_to_english("मला ताप आहे", "mr"), translate_from_english("Rest well.", "fr"), translate_to_english("x", None)):
            self.assertFalse(r["success"])
            self.assertIn("Unsupported", r["error"])
        load.assert_not_called()

    def test_generation_failure(self, load):
        with patch.object(translation, "_generate", side_effect=RuntimeError("boom")), self.assertLogs(translation.log):
            r = translate_to_english("నాకు జ్వరం ఉంది", "te")
        self.assertEqual((r["success"], r["text"], r["error"]), (False, None, translation.TRANSLATION_FAILED))

    def test_extraction_after_translation(self, load):
        with fake_generate("I have had a headache and fever for two days."):
            r = translate_to_english("నాకు రెండు రోజులుగా తలనొప్పి ఉంది", "te")
        info = extract_medical_info(r["text"], "en")
        self.assertEqual((set(info["symptoms"]), info["duration"]), ({"headache", "fever"}, "2 days"))


class TestModelUnavailable(unittest.TestCase):
    def test_load_failure(self):
        with patch.object(translation, "_load", side_effect=OSError("401 gated repo")), self.assertLogs(translation.log):
            r = translate_to_english("నాకు జ్వరం ఉంది", "te")
        self.assertEqual((r["success"], r["text"], r["error"]), (False, None, translation.MODEL_UNAVAILABLE))


if __name__ == "__main__":
    unittest.main()
