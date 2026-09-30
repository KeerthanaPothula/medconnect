"""MedConnect Streamlit UI. Phase 1: layout only, no AI processing yet."""
import streamlit as st

from modules.language import LANGUAGES

PENDING = "Not implemented yet (Phase 1 placeholder)."

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
        st.info(PENDING)
    else:
        st.warning("Please enter a patient message first.")
c1, c2 = st.columns(2)
c1.text_input("Detected language", value="—", disabled=True)
c2.text_input("English translation", value="—", disabled=True)
st.text_area("Medical information", value="—", disabled=True)
c3, c4 = st.columns(2)
c3.text_input("Symptoms", value="—", disabled=True)
c4.text_input("Duration", value="—", disabled=True)

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
