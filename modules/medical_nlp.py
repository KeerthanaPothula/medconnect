"""Rule-based extraction of symptoms and duration from patient text.

LIMITATION: only English rules exist so far. Text in Hindi, Telugu, Tamil or Kannada is not
analysed directly; the plan is to translate it to English first (Phase 3) and run these rules on
the translation. To add native-language rules later, add an entry to RULES below.
"""
import re

# --- English rules ---------------------------------------------------------

# canonical symptom -> regex alternatives (matched on lowercase text with word boundaries)
EN_SYMPTOMS = {
    "fever": r"fever\w*|high temperature",
    "headache": r"headaches?|head ?ache|head (?:pain|hurts|is hurting)|pain in (?:my |the )?head",
    "cough": r"cough\w*",
    "cold": r"cold|runny nose|blocked nose|stuffy nose",
    "sore throat": r"sore throat|throat (?:pain|hurts|is hurting)",
    "vomiting": r"vomit\w*|throwing up|threw up",
    "nausea": r"nause\w*",
    "diarrhea": r"diarrh(?:o)?ea|loose (?:motions?|stools?)",
    "dizziness": r"dizz\w*|giddy|giddiness|light-?headed",
    "stomach pain": r"stomach ?(?:ache|pain|hurts|is hurting)|(?:abdominal|belly) pain|pain in (?:my |the )?(?:stomach|belly|abdomen)",
    "chest pain": r"chest (?:pain|hurts|is hurting)|pain in (?:my |the )?chest",
    "back pain": r"back ?(?:ache|pain|hurts|is hurting)",
    "body pain": r"body ?(?:ache|pain)s?",
}
# Generic pain, only reported when no specific pain symptom matched.
EN_GENERIC_PAIN = r"pain\w*|aches?|hurts?|hurting"
EN_NEGATIONS = {"no", "not", "without", "don't", "dont", "never", "nor"}

NUMBER_WORDS = {"a": 1, "an": 1, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
EN_DURATION = re.compile(
    r"\b(\d+|" + "|".join(NUMBER_WORDS) + r"|several|few|a few|couple of|a couple of)\s+"
    r"(hour|day|night|week|month|year)s?\b"
)
EN_RELATIVE = [  # checked in order after numeric durations
    (r"\b(?:since )?last night\b", "since last night"),
    (r"\b(?:since )?yesterday\b", "since yesterday"),
    (r"\b(?:since )?(?:today|this morning)\b", "today"),
]


def _negated(text, start):
    # ponytail: looks up to 3 words back within the same clause; misses "fever? no." style negation.
    clause = re.split(r"[,.;!?]|\bbut\b", text[:start])[-1]
    return bool(EN_NEGATIONS & set(clause.split()[-3:]))


def _find(pattern, text):
    return [m for m in re.finditer(rf"\b(?:{pattern})\b", text) if not _negated(text, m.start())]


def _symptoms_en(text):
    found = [name for name, pattern in EN_SYMPTOMS.items() if _find(pattern, text)]
    if not any(s.endswith("pain") or s in ("headache", "sore throat") for s in found) and _find(EN_GENERIC_PAIN, text):
        found.append("pain")
    return found


def _duration_en(text):
    m = EN_DURATION.search(text)
    if m:
        qty, unit = m.groups()
        qty = NUMBER_WORDS.get(qty, qty)
        if qty in ("few", "a few", "couple of", "a couple of", "several"):
            return f"{qty.removeprefix('a ').removesuffix(' of')} {unit}s"
        return f"{qty} {unit}" + ("s" if int(qty) != 1 else "")
    for pattern, label in EN_RELATIVE:
        if re.search(pattern, text):
            return label
    return None


# language code -> (symptom extractor, duration extractor). Add new languages here.
RULES = {"en": (_symptoms_en, _duration_en)}


def extract_medical_info(text, lang="en"):
    """Return {"symptoms": [...], "duration": str or None, "supported": bool}.

    supported is False when no rules exist for `lang`; the other fields are then empty.
    """
    if lang not in RULES:
        return {"symptoms": [], "duration": None, "supported": False}
    symptoms, duration = RULES[lang]
    text = (text or "").lower()
    return {"symptoms": symptoms(text), "duration": duration(text), "supported": True}
