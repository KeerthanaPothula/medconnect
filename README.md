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

**Phase 2 — language detection + medical extraction (current, done):**

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
  "English translation" is still a placeholder for Phase 3.

**Known limitations of Phase 2**

- **Extraction rules are English only.** Hindi/Telugu/Tamil/Kannada messages are detected correctly but
  not analysed (`supported: False`, and the UI says so). The plan is to run the English rules on the
  Phase 3 translation. Native-language rules can be added as new entries in `RULES` in `medical_nlp.py`.
- `langdetect` is unreliable on very short Latin-script text (e.g. "fever 2 days" → Danish, 99.99%),
  hence the 3-word minimum. Very short messages are shown as "Uncertain"; plain-ASCII ones are still
  passed to the English rules.
- Keyword rules give false positives/negatives (e.g. "I feel cold" → `cold`) and handle only simple negation.
- `data/medical_samples.csv` is small, synthetic development data; its translations are not validated
  by native speakers and must not be treated as ground truth.

## Modules

| Module | Responsibility | Tech | Status |
|---|---|---|---|
| `modules/asr.py` | Speech-to-text | OpenAI Whisper | planned |
| `modules/language.py` | Language detection | langdetect | **Phase 2** |
| `modules/translation.py` | Indian language ↔ English | IndicTrans2 (Hugging Face) | planned |
| `modules/medical_nlp.py` | Symptoms / duration extraction | regex rules (English) | **Phase 2** |
| `modules/teachback.py` | Understanding verification | sentence-transformers | planned |

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
