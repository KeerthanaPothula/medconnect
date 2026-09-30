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
        at.text_area(key="patient_text").input("I have fever for 3 days")
        at.button[0].click().run()
        self.assertFalse(at.exception)
        self.assertTrue(at.info)
        for b in at.button[1:]:  # empty inputs -> warnings, no crash
            b.click().run()
            self.assertFalse(at.exception)
        self.assertTrue(at.warning)


if __name__ == "__main__":
    unittest.main()
