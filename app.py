"""MedConnect Streamlit UI. Phase 5: voice input (local Whisper), language detection, translation (IndicTrans2),
medical extraction, teach-back."""
import streamlit as st

from modules.asr import transcribe_audio
from modules.language import CODE_TO_NAME, LANGUAGES, detect_language
from modules.medical_nlp import extract_medical_info
from modules.teachback import NEEDS_CLARIFICATION, UNCERTAIN, UNDERSTOOD, verify_teachback
from modules.translation import translate_from_english, translate_to_english

SPINNER = "Translating... (the first translation loads the model and can take a minute)"

st.set_page_config(page_title="MedConnect", page_icon="🩺", layout="wide")
st.title("MEDCONNECT")
st.caption("Multilingual Healthcare Communication System — course-project prototype, not a diagnostic tool.")

# SECTION 1 — Patient
st.header("1. Patient")
patient_lang = st.selectbox("Patient language", list(LANGUAGES), key="patient_lang")
audio = st.audio_input("Voice input: record, then stop. The speech is transcribed into the message box below.",
                       key="patient_audio")
# Transcribe each new recording once, before the text box is created so its text can be filled in.
# Whisper is told the selected patient language (its own guess is unreliable on short Indic clips);
# changing the language re-transcribes the same recording.
if audio is not None and (audio.file_id, patient_lang) != st.session_state.get("transcribed_id"):
    st.session_state.transcribed_id = (audio.file_id, patient_lang)
    with st.spinner("Transcribing... (the first recording loads the speech model and can take a minute)"):
        st.session_state.asr_result = transcribe_audio(audio, language=LANGUAGES[patient_lang])
    if st.session_state.asr_result["success"]:
        st.session_state.patient_text = st.session_state.asr_result["text"]
asr = st.session_state.get("asr_result")
if asr and asr["success"]:
    st.success(f"Transcribed locally with Whisper as {CODE_TO_NAME[asr['language']]}. "
               "Check or correct the text, then click Process Patient Message.")
elif asr:
    st.warning(asr["error"])
patient_text = st.text_area("Describe your symptoms (type, or use voice input above)", key="patient_text")
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
st.caption("The patient explains the Section 3 instruction back in their own words, in any supported language.")
teachback = st.text_area("Patient's explanation in their own words", key="teachback")
if st.button("Check Understanding"):
    st.session_state.pop("teachback_result", None)
    if not instruction.strip():
        st.warning("Please enter the healthcare worker instruction in Section 3 first.")
    elif not teachback.strip():
        st.warning("Please enter the patient's response first.")
    else:
        # Short replies often defeat language detection; fall back to the patient language chosen in Section 3.
        code = detect_language(teachback)["code"] or LANGUAGES[target_lang]
        with st.spinner(SPINNER):
            tr = translate_to_english(teachback, code)
        if tr["success"]:
            st.session_state.teachback_result = {"english": tr["text"], "translated": code != "en",
                                                 **verify_teachback(instruction, tr["text"])}
        else:
            st.warning(f"{tr['error']} The patient's response could not be translated, so understanding was not checked.")

tb = st.session_state.get("teachback_result")
if tb:
    label = {UNDERSTOOD: (st.success, "✓ Understood"), NEEDS_CLARIFICATION: (st.warning, "⚠ Needs clarification"),
             UNCERTAIN: (st.info, "? Uncertain")}
    show, text = label[tb["status"]]
    show(f"**{text}** — {tb['feedback']}")
    if tb["translated"]:
        st.markdown(f"**Patient response in English:** {tb['english']}")
    if tb["score"] is not None:
        st.markdown(f"**Key points matched:** {len(tb['matched_concepts'])} of "
                    f"{len(tb['matched_concepts']) + len(tb['missing_concepts'])}")
    c5, c6 = st.columns(2)
    with c5:
        st.markdown("**Matched concepts:**")
        st.markdown("\n".join(f"- {c}" for c in tb["matched_concepts"]) or "None")
    with c6:
        st.markdown("**Missing concepts:**")
        st.markdown("\n".join(f"- {c}" for c in tb["missing_concepts"]) or "None")
    st.caption("Automatic keyword-based check, not a clinical assessment. Confirm understanding with the patient.")
