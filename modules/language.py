"""Automatic language detection for patient text using langdetect."""
from langdetect import DetectorFactory, LangDetectException, detect_langs

DetectorFactory.seed = 0  # langdetect is random by default; fix it so results are repeatable

# Supported languages: display name -> ISO 639-1 code.
LANGUAGES = {
    "English": "en",
    "Hindi": "hi",
    "Telugu": "te",
    "Tamil": "ta",
    "Kannada": "kn",
}
CODE_TO_NAME = {code: name for name, code in LANGUAGES.items()}

MIN_WORDS = 3          # langdetect gives confident wrong answers on 1-2 word Latin text ("fever 2 days" -> Danish)
MIN_CONFIDENCE = 0.80  # below this the top guess is reported as uncertain


def detect_language(text):
    """Return {"code": ISO code or None, "name": display text, "confidence": float or None}.

    code is None when the language could not be determined reliably; name then says why.
    """
    text = (text or "").strip()
    if not text:
        return {"code": None, "name": "Unknown (empty input)", "confidence": None}
    if sum(any(c.isalpha() for c in w) for w in text.split()) < MIN_WORDS:  # numbers don't count as words
        return {"code": None, "name": "Uncertain (message too short)", "confidence": None}
    try:
        best = detect_langs(text)[0]
    except LangDetectException:  # e.g. only digits/punctuation
        return {"code": None, "name": "Unknown (no language features found)", "confidence": None}
    if best.prob < MIN_CONFIDENCE:
        return {"code": None, "name": f"Uncertain (best guess '{best.lang}', {best.prob:.0%})", "confidence": best.prob}
    if best.lang not in CODE_TO_NAME:
        return {"code": None, "name": f"Unsupported language ('{best.lang}')", "confidence": best.prob}
    return {"code": best.lang, "name": CODE_TO_NAME[best.lang], "confidence": best.prob}
