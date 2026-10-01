"""MedConnect Streamlit UI. Phase 2: language detection + rule-based medical extraction."""
import streamlit as st

from modules.language import LANGUAGES, detect_language
from modules.medical_nlp import extract_medical_info

PENDING = "Not implemented yet (planned for a later phase)."

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
        # Undetermined language on plain ASCII text (e.g. "fever 2 days") still gets a try with the English rules.
        rules_lang = lang["code"] or ("en" if patient_text.isascii() else None)
        st.session_state.analysis = {"lang": lang, "info": extract_medical_info(patient_text, rules_lang)}
    else:
        st.session_state.pop("analysis", None)
        st.warning("Please enter a patient message first.")

analysis = st.session_state.get("analysis")
c1, c2 = st.columns(2)
with c1:
    st.markdown("**Detected Language:**")
    st.write(analysis["lang"]["name"] if analysis else "—")
with c2:
    st.markdown("**English Translation:**")
    st.caption("Placeholder — translation is planned for Phase 3.")

st.markdown("**Medical Information:**")
if analysis:
    info = analysis["info"]
    if not info["supported"]:
        st.info("Rule-based extraction currently supports English text only. "
                "Non-English messages will be analysed via their English translation in Phase 3.")
    else:
        c3, c4 = st.columns(2)
        with c3:
            st.markdown("Symptoms:")
            st.markdown("\n".join(f"- {s}" for s in info["symptoms"]) or "No symptoms detected")
        with c4:
            st.markdown("Duration:")
            st.write(info["duration"] or "No duration detected")
else:
    st.write("—")

# SECTION 3 — Healthcare Worker
st.header("3. Healthcare Worker")
instruction = st.text_area("Instruction for the patient (English)", key="instruction")
target_lang = st.selectbox("Target patient language", list(LANGUAGES), key="target_lang")
if st.button("Translate Instruction"):
    if instruction.strip():
        st.info(PENDING)
    else:
        st.warning("Please enter an instruction first.")
st.text_area("Translated instruction", value="—", disabled=True)

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
