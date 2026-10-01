# MedConnect

**Multilingual Healthcare Communication System** — a college course-project prototype.

> ⚠️ Not a medical diagnostic system. Uses only synthetic data; never enter real patient information.

## What it is

MedConnect helps a patient who speaks an Indian language and an English-speaking healthcare worker understand each other:

1. The patient describes symptoms by text or voice.
2. The message is transcribed (Whisper), its language detected, and translated to English.
3. Symptoms, duration and basic medical info are extracted for the healthcare worker.
4. The worker's instruction is translated back into the patient's language.
5. The patient explains the instruction back in their own words (*teach-back*).
6. The system checks understanding and reports **Understood** or **Needs clarification**, listing missing key points.

## Progress

**Phase 1 — skeleton (done):** Streamlit UI with all four sections, module stubs, synthetic datasets in `data/`, UI smoke test.

**Phase 2 — language detection + medical extraction (done):**

- `modules/language.py` → `detect_language(text)` uses `langdetect` and returns
  `{"code": "te", "name": "Telugu", "confidence": 0.99}`. Supported: English, Hindi, Telugu, Tamil, Kannada.
  `code` is `None` (and `name` says why) for empty input, messages with fewer than 3 words,
  low-confidence detections (< 80%), unsupported languages, and text with no letters.
- `modules/medical_nlp.py` → `extract_medical_info(text, lang="en")` is transparent, rule-based (regex) extraction returning
  `{"symptoms": ["fever", "cough"], "duration": "3 days", "supported": True}`.
  Symptoms covered: fever, headache, cough, cold, sore throat, vomiting, nausea, diarrhea, dizziness,
  stomach/chest/back/body pain, and generic pain. Durations: `2 days`, `two days`, `a week`, `2 weeks`,
  `several days`, `today`, `since yesterday`, `since last night`. Simple negation ("no fever") is skipped.
- The UI's **Process Patient Message** button shows the detected language, symptoms and duration.

**Known limitations of Phase 2**

- **Extraction rules are English only.** Since Phase 3, non-English messages are analysed via their English
  translation. Native-language rules can be added as new entries in `RULES` in `medical_nlp.py`.
- `langdetect` is unreliable on very short Latin-script text (e.g. "fever 2 days" → Danish, 99.99%),
  hence the 3-word minimum. Very short messages are shown as "Uncertain"; plain-ASCII ones are still
  passed to the English rules.
- Keyword rules give false positives/negatives (e.g. "I feel cold" → `cold`) and handle only simple negation.
- `data/medical_samples.csv` is small, synthetic development data; its translations are not validated
  by native speakers and must not be treated as ground truth.

**Phase 3 — translation (done):**

English is the internal pivot language:

```
Patient message ─▶ detect language ─▶ (non-English) translate to English ─▶ medical extraction (English rules)
Worker instruction (English) ─▶ translate to selected patient language
```

- `modules/translation.py` → `translate_to_english(text, source_language)` and
  `translate_from_english(text, target_language)` (ISO codes `en hi te ta kn`). Both return
  `{"success", "text", "source_language", "target_language", "error"}`. English ↔ English returns the
  input unchanged without loading any model. On failure they return `success: False`, `text: None`
  and a short error. They never raise and never return a made-up translation.
- Models: AI4Bharat **IndicTrans2** distilled 200M, MIT license, two models:
  `ai4bharat/indictrans2-indic-en-dist-200M` (Indic → English) and
  `ai4bharat/indictrans2-en-indic-dist-200M` (English → Indic). Language tags: `eng_Latn`, `hin_Deva`,
  `tel_Telu`, `tam_Taml`, `kan_Knda`. Pre/post-processing (normalisation, script unification) uses
  `IndicProcessor` from IndicTransToolkit.
- Download and storage: each model is downloaded on its first use into `models/` (git-ignored, about
  0.9 GB per model) and loaded into memory once per app process (`functools.lru_cache`), so later
  clicks reuse it. Runs on CPU. The first translation after a start takes noticeably longer.
- UI: Section 2 shows the original message, the detected language, the English translation and the extracted
  information. Section 3 translates the worker's English instruction to the selected language. If a
  model is unavailable the UI says *"Translation model unavailable. English processing is still
  available."* and English messages keep working.

**Known limitations of Phase 3**

- **Translation quality has not been evaluated.** No BLEU/chrF or human evaluation has been done yet.
  The 5-row sample CSV is not a test set. Medical terms may be mistranslated.
- Language detection decides the source language. If detection is uncertain (for example very short
  non-English text), the message is not translated.
- Text is split into sentences on `. ! ? ।` and newlines; long rambling sentences are truncated at 256 tokens.
- The models are gated on Hugging Face and need a one-time login (see below).

**Phase 4 — teach-back verification (done):**

*Teach-back* means the patient explains the healthcare worker's instruction back in their own words, so the
worker can check that it was understood. In MedConnect this checks only whether the patient's reply reflects
the instruction. **It is not a medical diagnosis or a clinical assessment.**

```
Worker instruction (English) ─▶ translate to patient language ─▶ patient replies in own language
   ─▶ translate reply to English (skipped for English) ─▶ verify_teachback(instruction, reply) ─▶ result
```

- `modules/teachback.py` → `verify_teachback(instruction, patient_response)` returns
  `{"status", "score", "matched_concepts", "missing_concepts", "contradictions", "feedback"}`.
- Explainable concept matching, with no ML model and no LLM. Both texts are normalised (lowercase,
  punctuation removed, number words → digits). Key concepts are then found with a small lexicon
  (`CONCEPTS`): food timing (after/before food), time of day, frequency (once/twice a day, every N hours),
  dose, duration, and actions (take medicine, drink fluids, rest, come back). Each instruction concept is
  then classified as:
  - **matched**: the reply has the same value ("after food" ≈ "after eating" ≈ "after a meal"),
  - **contradicted**: the reply gives another value in the same group ("before food"), or negates it ("I will not take…"),
  - **missing**: otherwise.
- Result: **✓ Understood** when all key concepts match. **⚠ Needs clarification** when anything is
  contradicted or missing; the missing points are listed. **? Uncertain** when the reply mentions none of
  the key concepts, or the instruction contains no recognisable concept. `score` = matched / key concepts.
- UI: Section 4 uses the Section 3 instruction and patient language. The reply's language is detected,
  falling back to the Section 3 language for short replies.
- `data/teachback_dataset.csv`: 12 **synthetic development examples** (correct, partially correct,
  incorrect, missing information, unrelated). The tests check that every label is reproduced; this is a
  regression check on hand-written examples, **not an accuracy measurement**.

**Known limitations of Phase 4**

- **No clinical validation** and no evaluation on real teach-back conversations has been performed.
- The lexicon is small and English-only. Instructions outside it (e.g. prohibitions such as "do not drive",
  diet advice) are reported as *Uncertain* or only partly checked. Unusual paraphrases are missed.
- Quality depends on the translation. The matcher only sees the English translation of the reply.
- Negation handling is simple (a negation word shortly before the concept, in the same clause).

**Phase 5 — voice input with local Whisper (current):**

```
Patient speaks ─▶ st.audio_input (WAV) ─▶ local Whisper ─▶ text in the message box (editable)
   ─▶ Process Patient Message ─▶ existing language detection ─▶ IndicTrans2 ─▶ medical extraction
```

- `modules/asr.py` → `transcribe_audio(audio_data, language=None)` returns
  `{"success", "text", "language", "error"}`. `language` is Whisper's own guess of the most likely
  language, with no confidence score. You can also pass a code to force a language. It never raises.
- **Runs locally, with no external or paid speech API**: the open-weights `openai/whisper-small` model
  (about 0.97 GB) runs on this machine via the already-installed `transformers` and `torch`, so no new
  packages were needed. Audio is decoded with Python's `wave` module (16-bit PCM WAV, which is what
  `st.audio_input` records), so ffmpeg is not needed.
- The model is downloaded once into `models/` (git-ignored) and loaded once per app process.
- UI: Section 1 has both text input and voice input. When a recording is stopped, it is transcribed once
  and the text is placed into the message box, where it can be corrected. **Process Patient Message**
  then runs the unchanged Phase 2–3 pipeline. The pipeline still uses `detect_language` on the text.
- **The selected Patient language is passed to Whisper** (`transcribe_audio(audio, language="te")` etc.)
  instead of letting Whisper guess. Its automatic guess was wrong on a short Telugu recording. Changing the
  dropdown re-transcribes the current recording. If the patient speaks a different language from the
  one selected, the transcript will be poor.
- Errors (no or empty or silent audio, unreadable audio, model unavailable, transcription failure, no speech) are
  shown as short messages. Typing still works.

Measured on this development laptop (CPU only, Intel Iris Xe, 16 GB RAM), single runs:
first load including download ≈ 72 s, later loads from disk ≈ 9 s, transcription of a 3-second clip ≈ 4–10 s.
**This is not real-time.**

**Known limitations of Phase 5**

- **Only English has been tested with real audio**: one synthetic Windows-TTS clip
  (`data/audio/en_headache_two_days.wav`), transcribed exactly. **Telugu, Hindi, Kannada and Tamil
  speech have not been tested**, because no local TTS voices for them exist on the development machine.
  Whisper-small is known to be weaker on these languages than on English. To test them, add synthetic
  recordings as `data/audio/<lang>_<name>.wav` and run the real test below.
- Transcription quality has **not been evaluated** and has **no clinical validation**.
- Only the first 30 seconds of a recording are transcribed (Whisper's input window).
- WAV input only (16-bit PCM). Other formats are rejected with a message.

## Modules

| Module | Responsibility | Tech | Status |
|---|---|---|---|
| `modules/asr.py` | Speech-to-text | Whisper small, local (transformers) | **Phase 5** |
| `modules/language.py` | Language detection | langdetect | **Phase 2** |
| `modules/translation.py` | Indian language ↔ English | IndicTrans2 dist-200M (Hugging Face) | **Phase 3** |
| `modules/medical_nlp.py` | Symptoms / duration extraction | regex rules (English) | **Phase 2** |
| `modules/teachback.py` | Teach-back verification | rule-based concept matching | **Phase 4** |

Heavy models will be optional: the app must still run (with clearly labelled fallback behaviour) if a model is unavailable.

## Project layout

```
app.py              Streamlit UI
modules/            Feature modules
data/               Synthetic test datasets
tests/              Tests
utils/              Shared helpers
models/             Runtime-downloaded models (git-ignored)
```

## Setup (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# IndicTransToolkit: PyPI 1.1.x has no Windows wheels (needs a C++ compiler), so install the
# pure-Python 1.0.2 from git. --no-build-isolation lets it build with setuptools<81 from requirements.txt.
pip install --no-build-isolation --no-deps "git+https://github.com/VarunGumma/IndicTransToolkit@0c607654e8"
```

macOS/Linux: `source .venv/bin/activate` instead of the second line.

Tested with Python 3.13 on Windows 11 (CPU only, 16 GB RAM).

### Enabling translation (one-time Hugging Face access)

The IndicTrans2 models are gated: access is free and approved automatically, but downloading needs a login.

1. Create or log in to an account at https://huggingface.co.
2. Open both model pages and accept the terms:
   - https://huggingface.co/ai4bharat/indictrans2-indic-en-dist-200M
   - https://huggingface.co/ai4bharat/indictrans2-en-indic-dist-200M
3. Create a **Read** token at https://huggingface.co/settings/tokens.
4. Run `huggingface-cli login` (inside the activated venv) and paste the token.

Without this, the app still runs; translation is reported as unavailable.

## Run

```powershell
streamlit run app.py
```

Opens at http://localhost:8501.

## Test

```powershell
python -m unittest discover tests
```

Unit tests mock the translation model, so they need no download or login. The real-model integration
test is skipped by default. It downloads the models on first run:

```powershell
$env:MEDCONNECT_REAL_MODEL = "1"; python -m unittest tests.test_translation_real -v
$env:MEDCONNECT_REAL_MODEL = "1"; python -m unittest tests.test_asr_real -v   # Whisper, ~0.97 GB on first run
```
