import time
from langdetect import detect, LangDetectException
from deep_translator import GoogleTranslator

class TranslationError(Exception):
    """Custom exception raised when translation fails."""
    pass

def translate_text(text, source_lang='auto', target_lang='en'):
    """
    Translates input text into the target language.
    Detects source language via langdetect if source_lang is 'auto'.
    Returns a tuple: (translated_text, detected_source_lang_code).
    Wraps failures in TranslationError with one retry.
    """
    text = text.strip()
    if not text:
        return "", source_lang

    # Detect source language if set to auto
    detected_lang = source_lang
    if source_lang == 'auto':
        try:
            detected_lang = detect(text)
        except LangDetectException:
            detected_lang = 'en'  # Fallback to English

    # If source and target are the same, no translation needed
    if detected_lang == target_lang:
        return text, detected_lang

    # Translation loop with one retry
    attempts = 2
    for attempt in range(attempts):
        try:
            # Primary Engine: Argos Translate (Local, offline)
            # We wrap it in a try-except. If the models are not loaded/installed,
            # we fallback to deep-translator immediately.
            try:
                import argostranslate.package
                import argostranslate.translate
                
                # Check if language pair is installed
                installed_languages = argostranslate.translate.get_installed_languages()
                from_lang = list(filter(lambda x: x.code == detected_lang, installed_languages))
                to_lang = list(filter(lambda x: x.code == target_lang, installed_languages))
                
                if from_lang and to_lang:
                    translation = from_lang[0].get_translation(to_lang[0])
                    translated_text = translation.translate(text)
                    return translated_text, detected_lang
                else:
                    # Model not installed, we fallback to online translator
                    raise Exception("Argos Translation model not installed for this language pair.")
            except Exception as argos_err:
                # Fallback to deep-translator (Google Translate free API)
                translator = GoogleTranslator(source=detected_lang, target=target_lang)
                translated_text = translator.translate(text)
                if not translated_text:
                    raise TranslationError("Translated text is empty.")
                return translated_text, detected_lang

        except Exception as e:
            if attempt == attempts - 1:
                raise TranslationError(f"Translation failed after {attempts} attempts: {str(e)}")
            time.sleep(1)  # Brief pause before retry
