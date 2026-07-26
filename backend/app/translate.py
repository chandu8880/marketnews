import logging

from deep_translator import GoogleTranslator

logger = logging.getLogger("translate")


def translate_text(text: str, target_lang: str = "te") -> str:
    text = text.strip()
    if not text:
        return ""
    try:
        return GoogleTranslator(source="en", target=target_lang).translate(text)
    except Exception:
        logger.exception("Translation failed for target_lang=%s", target_lang)
        raise
