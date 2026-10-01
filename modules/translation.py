"""Indian-language <-> English translation with IndicTrans2 (AI4Bharat).

English is the internal pivot language: patient text is translated to English for medical extraction,
and English healthcare-worker instructions are translated to the patient's language.

Models (Hugging Face, gated: needs a free HF account, accepted model terms and `hf auth login`):
  Indic -> English: ai4bharat/indictrans2-indic-en-dist-200M
  English -> Indic: ai4bharat/indictrans2-en-indic-dist-200M
Each is downloaded once on first use into models/ and loaded into memory once per process.

If a model cannot be loaded or fails, the functions return success=False with a short error;
they never raise and never return a made-up translation.
"""
import functools
import logging
import re
from pathlib import Path

log = logging.getLogger(__name__)

MODELS = {
    "to_en": "ai4bharat/indictrans2-indic-en-dist-200M",
    "from_en": "ai4bharat/indictrans2-en-indic-dist-200M",
}
MODEL_DIR = Path(__file__).resolve().parent.parent / "models"

# ISO 639-1 code -> IndicTrans2 (FLORES-200 style) language tag.
IT2_CODES = {"en": "eng_Latn", "hi": "hin_Deva", "te": "tel_Telu", "ta": "tam_Taml", "kn": "kan_Knda"}

MODEL_UNAVAILABLE = "Translation model unavailable."
TRANSLATION_FAILED = "Translation failed."


@functools.lru_cache(maxsize=None)  # load each model once per process; failures are not cached, so a retry can succeed
def _load(direction):
    import torch  # heavy imports only when translation is actually used
    from IndicTransToolkit.processor import IndicProcessor
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    name = MODELS[direction]
    tokenizer = AutoTokenizer.from_pretrained(name, trust_remote_code=True, cache_dir=MODEL_DIR)
    model = AutoModelForSeq2SeqLM.from_pretrained(name, trust_remote_code=True, cache_dir=MODEL_DIR)
    model.eval()
    return tokenizer, model, IndicProcessor(inference=True), torch


def _generate(bundle, sentences, src, tgt):
    tokenizer, model, processor, torch = bundle
    batch = processor.preprocess_batch(sentences, src_lang=src, tgt_lang=tgt)
    inputs = tokenizer(batch, truncation=True, padding="longest", return_tensors="pt", return_attention_mask=True)
    with torch.no_grad():
        # use_cache=False: IndicTrans2's remote model code expects legacy tuple KV caches and crashes with the
        # cache objects transformers 4.57 passes. ponytail: slower decoding; fine for short patient messages.
        out = model.generate(**inputs, max_length=256, num_beams=5, num_return_sequences=1, use_cache=False)
    decoded = tokenizer.batch_decode(out, skip_special_tokens=True, clean_up_tokenization_spaces=True)
    return processor.postprocess_batch(decoded, lang=tgt)


def _translate(text, src, tgt):
    result = {"success": False, "text": None, "source_language": src, "target_language": tgt, "error": None}
    text = text.strip() if isinstance(text, str) else ""
    if not text:
        return {**result, "error": "Empty input."}
    if src not in IT2_CODES or tgt not in IT2_CODES:
        return {**result, "error": f"Unsupported language: {src if src not in IT2_CODES else tgt}."}
    if src == tgt:
        return {**result, "success": True, "text": text}

    # IndicTrans2 is sentence-level: split on sentence punctuation (incl. Devanagari danda) and newlines.
    sentences = [s for s in re.split(r"(?<=[.!?।])\s+|\n+", text) if s.strip()]
    try:
        bundle = _load("to_en" if tgt == "en" else "from_en")
    except Exception:
        log.exception("Loading translation model failed")
        return {**result, "error": MODEL_UNAVAILABLE}
    try:
        translated = _generate(bundle, sentences, IT2_CODES[src], IT2_CODES[tgt])
    except Exception:
        log.exception("Translation failed")
        return {**result, "error": TRANSLATION_FAILED}
    return {**result, "success": True, "text": " ".join(translated)}


def translate_to_english(text, source_language):
    """Translate patient text (ISO code: en/hi/te/ta/kn) to English. English input is returned unchanged."""
    return _translate(text, source_language, "en")


def translate_from_english(text, target_language):
    """Translate English text to the patient's language (ISO code). English target returns the input unchanged."""
    return _translate(text, "en", target_language)
