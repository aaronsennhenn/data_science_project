from deep_translator import GoogleTranslator

def translate_text_all_capitalized(text: str) -> str:
    translator = GoogleTranslator(source='de', target='en')
    translated_text = translator.translate(text)
    return translated_text.title()

def translate_text_first_word_capitalized(text: str) -> str:
    translator = GoogleTranslator(source='de', target='en')
    translated = translator.translate(text)
    return translated.capitalize()
