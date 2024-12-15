import argostranslate.package
import argostranslate.translate

import warnings
warnings.filterwarnings("ignore")


# Download and install Argos Translate package
argostranslate.package.update_package_index()
available_packages = argostranslate.package.get_available_packages()

# Specify the translation direction
from_code = "en"
to_code = "de"

# Install the appropriate translation package
package_to_install = next(filter(lambda x: x.from_code == from_code and x.to_code == to_code, available_packages))
argostranslate.package.install_from_path(package_to_install.download())

# List of English sentences to translate
english_sentences = [
    "Hello World",
    "How are you?",
    "What is your name?",
    "I love programming.",
    "The weather is nice today.",
    "I am learning German.",
    "Can you help me?",
    "Where is the nearest restaurant?",
    "I would like a coffee.",
    "Thank you very much.",
    "Good morning.",
    "Good night.",
    "See you later.",
    "I am from the United States.",
    "I am a student.",
    "This is my friend.",
    "I like to travel.",
    "What time is it?",
    "I am hungry.",
    "Do you speak English?",
    "I need directions.",
    "How much does this cost?",
    "I am looking for a hotel.",
    "I have a reservation.",
    "Can I pay by credit card?",
    "I am allergic to peanuts.",
    "I need a doctor.",
    "Call the police.",
    "I lost my passport.",
    "Where is the bathroom?",
    "I am tired.",
    "I am happy.",
    "I am sad.",
    "I am excited.",
    "I am bored.",
    "I am angry.",
    "I am surprised.",
    "I am scared.",
    "I am confused.",
    "I am thirsty.",
    "I am cold.",
    "I am hot.",
    "I am wet.",
    "I am dry.",
    "I am clean.",
    "I am dirty.",
    "I am busy.",
    "I am free.",
    "I am ready.",
    "I am late."
]

# Translate each sentence and print the result
for sentence in english_sentences:
    translated_text = argostranslate.translate.translate(sentence, from_code, to_code)
    print(translated_text)
