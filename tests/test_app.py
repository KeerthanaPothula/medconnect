"""Smoke test: the Streamlit app renders and its buttons run without exceptions.

Run: python -m unittest discover tests
"""
import unittest

from streamlit.testing.v1 import AppTest


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

    def test_process_telugu_message(self):
        at = AppTest.from_file("../app.py").run()
        at.text_area(key="patient_text").input("నాకు రెండు రోజులుగా తలనొప్పి ఉంది")
        at.button[0].click().run()
        self.assertFalse(at.exception)
        self.assertIn("Telugu", " ".join(str(e.value) for e in at.markdown))
        self.assertIn("English text only", at.info[0].value)


if __name__ == "__main__":
    unittest.main()
