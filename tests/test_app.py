"""Smoke test: the Streamlit app renders and its buttons run without exceptions.

Run: python -m unittest discover tests
"""
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from modules import translation


class TestApp(unittest.TestCase):
    def test_renders_all_sections(self):
        at = AppTest.from_file("../app.py").run()
        self.assertFalse(at.exception)
        headers = [h.value for h in at.header]
        self.assertEqual(len(headers), 4)
        self.assertEqual(len(at.button), 3)

    def test_buttons_run_without_error(self):
        at = AppTest.from_file("../app.py").run()
        for b in at.button:  # empty inputs -> warnings, no crash
            b.click().run()
            self.assertFalse(at.exception)
        self.assertTrue(at.warning)

    def test_process_english_message(self):
        at = AppTest.from_file("../app.py").run()
        at.text_area(key="patient_text").input("I have had fever and cough for three days")
        at.button[0].click().run()
        self.assertFalse(at.exception)
        text = " ".join(str(e.value) for e in at.markdown)
        self.assertIn("English", text)
        self.assertIn("- fever\n- cough", text)
        self.assertIn("3 days", text)
        at.button[1].click().run()  # another button's rerun keeps the analysis on screen
        self.assertIn("3 days", " ".join(str(e.value) for e in at.markdown))

    def test_process_message_without_symptoms(self):
        at = AppTest.from_file("../app.py").run()
        at.text_area(key="patient_text").input("Hello, I would like to book an appointment please")
        at.button[0].click().run()
        text = " ".join(str(e.value) for e in at.markdown)
        self.assertIn("No symptoms detected", text)
        self.assertIn("No duration detected", text)

    def test_short_ascii_message_still_extracted(self):
        at = AppTest.from_file("../app.py").run()
        at.text_area(key="patient_text").input("fever 2 days")
        at.button[0].click().run()
        text = " ".join(str(e.value) for e in at.markdown)
        self.assertIn("too short", text)
        self.assertIn("- fever", text)

    # Non-English tests mock the model (see test_translation.py); the app imports the same module object.
    @patch.object(translation, "_load", return_value=object())
    @patch.object(translation, "_generate", return_value=["I have had a headache for two days."])
    def test_telugu_message_is_translated_then_extracted(self, gen, load):
        at = AppTest.from_file("../app.py").run()
        at.text_area(key="patient_text").input("నాకు రెండు రోజులుగా తలనొప్పి ఉంది")
        at.button[0].click().run()
        self.assertFalse(at.exception)
        text = " ".join(str(e.value) for e in at.markdown)
        self.assertIn("Telugu", text)
        self.assertIn("నాకు రెండు రోజులుగా తలనొప్పి ఉంది", text)  # original kept
        self.assertIn("I have had a headache for two days.", text)
        self.assertIn("- headache", text)
        self.assertIn("2 days", text)

    @patch.object(translation, "_load", side_effect=OSError("model not downloaded"))
    def test_translation_unavailable_does_not_crash(self, load):
        at = AppTest.from_file("../app.py").run()
        at.text_area(key="patient_text").input("मुझे तीन दिन से बुखार है")
        with self.assertLogs(translation.log):
            at.button[0].click().run()
        self.assertFalse(at.exception)
        self.assertIn("Hindi", " ".join(str(e.value) for e in at.markdown))
        self.assertEqual(at.warning[0].value, "Translation model unavailable. English processing is still available.")
        # English still works afterwards
        at.text_area(key="patient_text").input("I have had a cough for one week")
        at.button[0].click().run()
        self.assertIn("- cough", " ".join(str(e.value) for e in at.markdown))

    @patch.object(translation, "_load", return_value=object())
    @patch.object(translation, "_generate", return_value=["<fake model output>"])
    def test_instruction_translation(self, gen, load):
        at = AppTest.from_file("../app.py").run()
        at.text_area(key="instruction").input("Take the medicine after food.")
        at.selectbox(key="target_lang").select("Kannada")
        at.button[1].click().run()
        self.assertFalse(at.exception)
        self.assertEqual(gen.call_args.args[2:], ("eng_Latn", "kan_Knda"))
        self.assertIn("<fake model output>", " ".join(str(e.value) for e in at.markdown))

    @patch.object(translation, "_load", side_effect=OSError("model not downloaded"))
    def test_instruction_translation_unavailable(self, load):
        at = AppTest.from_file("../app.py").run()
        at.text_area(key="instruction").input("Take the medicine after food.")
        at.selectbox(key="target_lang").select("Tamil")
        with self.assertLogs(translation.log):
            at.button[1].click().run()
        self.assertFalse(at.exception)
        self.assertIn("could not be translated", at.warning[0].value)


if __name__ == "__main__":
    unittest.main()
