"""MedConnect Streamlit UI. Phase 3: language detection, translation (IndicTrans2), medical extraction."""
import streamlit as st

from modules.language import LANGUAGES, detect_language
from modules.medical_nlp import extract_medical_info
from modules.translation import translate_from_english, translate_to_english

PENDING = "Not implemented yet (planned for a later phase)."
SPINNER = "Translating... (the first translation loads the model and can take a minute)"

st.set_page_config(page_title="MedConnect", page_icon="🩺", layout="wide")
st.title("MEDCONNECT")
st.caption("Multilingual Healthcare Communication System — course-project prototype, not a diagnostic tool.")

# SECTION 1 — Patient
st.header("1. Patient")
patient_lang = st.selectbox("Patient language", list(LANGUAGES), key="patient_lang")
patient_text = st.text_area("Describe your symptoms", key="patient_text")
st.audio_input("Voice input (coming in a later phase)", disabled=True, key="patient_audio")
process = st.button("Process Patient Message", type="primary")

# SECTION 2 — Patient Analysis
st.header("2. Patient Analysis")
if process:
    if patient_text.strip():
        lang = detect_language(patient_text)
        code = lang["code"]
        if code == "en" or (code is None and patient_text.isascii()):
            # English, or short ASCII text like "fever 2 days" that langdetect can't classify: use as-is.
            english, error = patient_text, None
        elif code:
            with st.spinner(SPINNER):
                tr = translate_to_english(patient_text, code)
            english, error = tr["text"], tr["error"]
        else:
            english, error = None, "Language could not be detected reliably, so the message was not translated."
        st.session_state.analysis = {
            "original": patient_text, "lang": lang, "english": english, "error": error,
            "info": extract_medical_info(english, "en") if english else None,
        }
    else:
        st.session_state.pop("analysis", None)
        st.warning("Please enter a patient message first.")

analysis = st.session_state.get("analysis")
c1, c2 = st.columns(2)
with c1:
    st.markdown("**Detected Language:**")
    st.write(analysis["lang"]["name"] if analysis else "—")
    st.markdown("**English Translation:**")
    if not analysis:
        st.write("—")
    elif analysis["error"]:
        st.warning(f"{analysis['error']} English processing is still available.")
    elif analysis["english"] == analysis["original"]:
        st.write("Not needed — message processed as English.")
    else:
        st.write(analysis["english"])
with c2:
    st.markdown("**Original Patient Message:**")
    st.write(analysis["original"] if analysis else "—")

st.markdown("**Medical Information:**")
if not analysis:
    st.write("—")
elif not analysis["info"]:
    st.info("No English text is available for this message, so medical information could not be extracted.")
else:
    info = analysis["info"]
    c3, c4 = st.columns(2)
    with c3:
        st.markdown("Symptoms:")
        st.markdown("\n".join(f"- {s}" for s in info["symptoms"]) or "No symptoms detected")
    with c4:
        st.markdown("Duration:")
        st.write(info["duration"] or "No duration detected")

# SECTION 3 — Healthcare Worker
st.header("3. Healthcare Worker")
instruction = st.text_area("Instruction for the patient (English)", key="instruction")
target_lang = st.selectbox("Target patient language", list(LANGUAGES), key="target_lang")
if st.button("Translate Instruction"):
    if instruction.strip():
        with st.spinner(SPINNER):
            st.session_state.instruction_result = translate_from_english(instruction, LANGUAGES[target_lang])
    else:
        st.session_state.pop("instruction_result", None)
        st.warning("Please enter an instruction first.")
st.markdown("**Translated Instruction:**")
result = st.session_state.get("instruction_result")
if not result:
    st.write("—")
elif result["success"]:
    st.write(result["text"])
else:
    st.warning(f"{result['error']} The instruction could not be translated.")

# SECTION 4 — Patient Teach-back
st.header("4. Patient Teach-back")
teachback = st.text_area("Patient's explanation in their own words", key="teachback")
if st.button("Check Understanding"):
    if teachback.strip():
        st.info(PENDING)
    else:
        st.warning("Please enter the patient's response first.")
c5, c6 = st.columns(2)
c5.text_input("Understanding status", value="—", disabled=True)
c6.text_input("Similarity / result", value="—", disabled=True)
c7, c8 = st.columns(2)
c7.text_area("Important information", value="—", disabled=True)
c8.text_area("Missing information", value="—", disabled=True)
