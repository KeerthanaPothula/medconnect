"""Teach-back verification: does the patient's (English) response repeat the instruction's key concepts?

Explainable, rule-based concept matching (no ML model, no LLM):
1. Normalise both texts (lowercase, drop punctuation except clause marks, number words -> digits).
2. Find key concepts in the instruction using the CONCEPTS lexicon below.
3. Look for the same concepts in the response. A concept counts as
   - matched: the response contains the same value (e.g. "after food" ~ "after eating"),
   - contradicted: the response gives a different value in the same group ("before food"),
     or negates it ("I will not take the medicine"),
   - missing: otherwise.
4. Status: any contradiction or missing concept -> needs_clarification; all matched -> understood;
   nothing recognisable in the instruction, or no concept mentioned at all in the response -> uncertain.

LIMITATION: English only (non-English responses are translated first), small fixed lexicon,
instructions phrased as prohibitions ("do not drive") are not modelled. Not a medical judgement.
"""
import re

from modules.medical_nlp import NUMBER_WORDS, _negated

UNDERSTOOD, NEEDS_CLARIFICATION, UNCERTAIN = "understood", "needs_clarification", "uncertain"

# group -> [(regex, value)]. Values in the same group are mutually exclusive alternatives;
# a value may use regex backreferences (\1). Applied to normalised text.
CONCEPTS = {
    "food timing": [
        (r"after (?:(?:a|the|my|your) )?(?:food|eating|meals?|breakfast|lunch|dinner|(?:i|you) eat)|post[- ]?meals?", "after food"),
        (r"before (?:(?:a|the|my|your) )?(?:food|eating|meals?|breakfast|lunch|dinner|(?:i|you) eat)|(?:on an? |on )?empty stomach", "before food"),
    ],
    "time of day": [
        (r"morning", "in the morning"),
        (r"night|bedtime|before (?:going to )?(?:sleep\w*|bed)", "at night"),
    ],
    "frequency": [
        (r"once (?:a|per|every) day|once daily|1 time (?:a|per) day", "once a day"),
        (r"twice|2 times", "twice a day"),
        (r"thrice|3 times", "three times a day"),
        (r"every (\d+) hours?", r"every \1 hours"),
    ],
    "dose": [(r"(\d+) (?:\w+ )?(?:tablets?|pills?|capsules?)", r"\1 tablet(s)"),
             (r"(\d+) (?:tea|table)?spoons?(?:ful)?", r"\1 spoon(s)")],
    "duration": [(r"(\d+) (day|week|month)s?", r"\1 \2(s)")],
    "take medicine": [(r"(?:take|taking|have|use) (?:\w+ ){0,4}?(?:medicines?|medication|tablets?|pills?|capsules?|syrup|drops|dose)",
                       "take the medicine")],
    "drink fluids": [(r"drink (?:\w+ ){0,4}?(?:water|fluids?|liquids?)", "drink water/fluids")],
    "rest": [(r"\brest\b|sleep well", "rest")],
    "return": [(r"come back|return|visit (?:again|the (?:clinic|hospital|doctor))|see (?:a|the) doctor", "come back / see the doctor")],
}


def _normalize(text):
    text = re.sub(r"[^\w\s,.;!?']", " ", (text or "").lower())
    text = re.sub(r"\b(" + "|".join(w for w in NUMBER_WORDS if w not in ("a", "an")) + r")\b",
                  lambda m: str(NUMBER_WORDS[m.group()]), text)
    return " ".join(text.split())


def _concepts(text):
    """Return {group: {value: negated?}} for every concept found in normalised text."""
    found = {}
    for group, options in CONCEPTS.items():
        for pattern, value in options:
            for m in re.finditer(rf"\b(?:{pattern})\b", text):
                v = m.expand(value)
                found.setdefault(group, {})[v] = found.get(group, {}).get(v, True) and _negated(text, m.start())
    return found


def verify_teachback(instruction, patient_response):
    """Compare an English instruction with the patient's English teach-back response.

    Returns {"status", "score", "matched_concepts", "missing_concepts", "contradictions", "feedback"};
    score is matched / key concepts (None when the instruction has no recognisable concepts).
    """
    # Negated mentions in the instruction ("after food, not before food") are not expected concepts.
    expected = {g: {v for v, neg in d.items() if not neg} for g, d in _concepts(_normalize(instruction)).items()}
    expected = {g: v for g, v in expected.items() if v}
    response = _concepts(_normalize(patient_response))
    result = {"status": UNCERTAIN, "score": None, "matched_concepts": [], "missing_concepts": [], "contradictions": []}
    if not expected:
        return {**result, "feedback": "No key concepts were recognised in the instruction, so understanding "
                                      "cannot be checked automatically. Please check with the patient directly."}

    for group, values in expected.items():
        said = response.get(group, {})
        for value in sorted(values):
            if said.get(value) is False:
                result["matched_concepts"].append(value)
            else:
                result["missing_concepts"].append(value)
                if said.get(value):  # mentioned, but negated
                    result["contradictions"].append(f"instruction says '{value}', but the patient said they would not")
        result["contradictions"] += [f"instruction says '{' / '.join(sorted(values))}', but the patient said '{v}'"
                                     for v, neg in said.items() if v not in values and not neg]

    total = sum(len(v) for v in expected.values())
    result["score"] = round(len(result["matched_concepts"]) / total, 2)
    if result["contradictions"]:
        status = NEEDS_CLARIFICATION
        feedback = "Clarify: " + "; ".join(result["contradictions"]) + "."
    elif not result["missing_concepts"]:
        status = UNDERSTOOD
        feedback = "The patient repeated all key points."
    elif not result["matched_concepts"]:
        status = UNCERTAIN
        feedback = "The response does not mention any key point of the instruction. Ask the patient to explain it again."
    else:
        status = NEEDS_CLARIFICATION
        feedback = "Clarify the missing points: " + ", ".join(result["missing_concepts"]) + "."
    return {**result, "status": status, "feedback": feedback}
