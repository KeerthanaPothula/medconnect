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

## Current phase: Phase 1 — skeleton

- Streamlit UI with all four sections (inputs + result placeholders).
- Module files created as empty stubs; **no AI functionality yet**. Buttons show a "not implemented" message.
- Synthetic sample datasets in `data/`.
- Smoke test for the UI.

## Planned modules

| Module | Responsibility | Planned tech |
|---|---|---|
| `modules/asr.py` | Speech-to-text | OpenAI Whisper |
| `modules/language.py` | Language detection | langdetect |
| `modules/translation.py` | Indian language ↔ English | IndicTrans2 (Hugging Face) |
| `modules/medical_nlp.py` | Symptoms / duration extraction | rules + pretrained NLP |
| `modules/teachback.py` | Understanding verification | sentence-transformers |

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
```

macOS/Linux: `source .venv/bin/activate` instead of the second line.

## Run

```powershell
streamlit run app.py
```

Opens at http://localhost:8501.

## Test

```powershell
python -m unittest discover tests
```
