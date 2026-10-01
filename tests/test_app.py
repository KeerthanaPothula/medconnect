"""Smoke test: the Streamlit app renders and its buttons run without exceptions.

Run: python -m unittest discover tests
"""
import io
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

import streamlit

from modules import asr, translation
from tests.test_asr import make_wav


class FakeRecording(io.BytesIO):
    """Stands in for st.audio_input's UploadedFile (AppTest cannot drive the real audio widget)."""
    file_id = "recording-1"


def fake_audio_input(*args, **kwargs):
    return FakeRecording(make_wav())


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

    def _teachback(self, instruction, response, lang="English"):
        at = AppTest.from_file("../app.py").run()
        at.text_area(key="instruction").input(instruction)
        at.selectbox(key="target_lang").select(lang)
        at.text_area(key="teachback").input(response)
        at.button[2].click().run()
        self.assertFalse(at.exception)
        return at

    def test_teachback_understood(self):
        at = self._teachback("Take the medicine after food.", "I will take the medicine after eating.")
        self.assertIn("✓ Understood", at.success[0].value)
        self.assertIn("- after food", " ".join(str(e.value) for e in at.markdown))

    def test_teachback_needs_clarification(self):
        at = self._teachback("Take the medicine after food.", "I will take the medicine before food.")
        self.assertIn("⚠ Needs clarification", at.warning[0].value)
        self.assertIn("before food", at.warning[0].value)
        self.assertIn("- after food", " ".join(str(e.value) for e in at.markdown))  # listed as missing

    def test_teachback_requires_instruction(self):
        at = self._teachback("", "I will take the medicine.")
        self.assertIn("Section 3", at.warning[0].value)

    @patch.object(translation, "_load", return_value=object())
    @patch.object(translation, "_generate", return_value=["I will take the medicine after eating."])
    def test_teachback_telugu_response_is_translated(self, gen, load):
        at = self._teachback("Take the medicine after food.", "నేను భోజనం తర్వాత మందు వేసుకుంటాను", "Telugu")
        self.assertEqual(gen.call_args.args[2:], ("tel_Telu", "eng_Latn"))
        self.assertIn("✓ Understood", at.success[0].value)
        self.assertIn("I will take the medicine after eating.", " ".join(str(e.value) for e in at.markdown))

    @patch.object(translation, "_load", side_effect=OSError("model not downloaded"))
    def test_teachback_translation_unavailable(self, load):
        at = AppTest.from_file("../app.py").run()
        at.text_area(key="instruction").input("Take the medicine after food.")
        at.text_area(key="teachback").input("నేను భోజనం తర్వాత మందు వేసుకుంటాను")
        with self.assertLogs(translation.log):
            at.button[2].click().run()
        self.assertFalse(at.exception)
        self.assertIn("understanding was not checked", at.warning[0].value)
        self.assertFalse(at.success)

    # --- Voice input (Phase 5): st.audio_input is replaced by a fake recording, Whisper is mocked.

    @patch.object(streamlit, "audio_input", fake_audio_input)
    @patch.object(asr, "_load", return_value=object())
    @patch.object(asr, "_transcribe", return_value=("I have had a headache for two days.", "en"))
    def test_voice_english_fills_text_and_runs_pipeline(self, tr, load):
        at = AppTest.from_file("../app.py").run()
        self.assertFalse(at.exception)
        self.assertEqual(at.text_area(key="patient_text").value, "I have had a headache for two days.")
        self.assertIn("Whisper", at.success[0].value)
        at.button[0].click().run()  # Process Patient Message: existing pipeline, unchanged
        text = " ".join(str(e.value) for e in at.markdown)
        self.assertIn("English", text)
        self.assertIn("- headache", text)
        self.assertIn("2 days", text)
        self.assertEqual(tr.call_count, 1)  # same recording is not re-transcribed on reruns

    @patch.object(streamlit, "audio_input", fake_audio_input)
    @patch.object(asr, "_load", return_value=object())
    @patch.object(asr, "_transcribe", return_value=("నాకు రెండు రోజులుగా తలనొప్పి ఉంది", "te"))
    @patch.object(translation, "_load", return_value=object())
    @patch.object(translation, "_generate", return_value=["I have had a headache for two days."])
    def test_voice_telugu_goes_through_detection_and_translation(self, gen, tload, tr, load):
        at = AppTest.from_file("../app.py").run()
        self.assertIn("Telugu", at.success[0].value)
        at.button[0].click().run()
        self.assertFalse(at.exception)
        self.assertEqual(gen.call_args.args[2:], ("tel_Telu", "eng_Latn"))
        text = " ".join(str(e.value) for e in at.markdown)
        self.assertIn("- headache", text)
        self.assertIn("2 days", text)

    @patch.object(streamlit, "audio_input", fake_audio_input)
    @patch.object(asr, "_load", side_effect=OSError("model not downloaded"))
    def test_voice_model_unavailable_does_not_crash(self, load):
        with self.assertLogs(asr.log):
            at = AppTest.from_file("../app.py").run()
        self.assertFalse(at.exception)
        self.assertEqual(at.warning[0].value, asr.MODEL_UNAVAILABLE)
        self.assertEqual(at.text_area(key="patient_text").value, "")
        at.text_area(key="patient_text").input("I have had fever for three days")  # typing still works
        at.button[0].click().run()
        self.assertIn("- fever", " ".join(str(e.value) for e in at.markdown))


if __name__ == "__main__":
    unittest.main()
