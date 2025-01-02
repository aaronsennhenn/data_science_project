from deep_translator import GoogleTranslator
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


def translate_text_all_capitalized(text: str) -> str:
    translator = GoogleTranslator(source='de', target='en')
    translated_text = translator.translate(text)
    return translated_text.title()

def translate_text_first_word_capitalized(text: str) -> str:
    translator = GoogleTranslator(source='de', target='en')
    translated = translator.translate(text)
    return translated.capitalize()


def compute_cosine_similarity(user_vector_str, dish_embedding_str):
    """
    Computes the cosine similarity between a user vector and a dish embedding.
    Handles input vectors stored as strings in list form.

    Args:
        user_vector_str (str): The vector representing the user's preferences, stored as a string.
        dish_embedding_str (str): The vector representing the dish's embedding, stored as a string.

    Returns:
        float: The cosine similarity score between the user vector and the dish embedding.
    """
    # Convert string inputs to NumPy arrays
    user_vector = np.array(eval(user_vector_str))
    dish_embedding = np.array(eval(dish_embedding_str))

    # Compute cosine similarity
    score = cosine_similarity(user_vector.reshape(1, -1), dish_embedding.reshape(1, -1))[0, 0]

    return round(score,3)

def correct_icons(dish_name,menuLine):
    if not dish_name:
        return np.nan
    

    dish_lower = str(dish_name).lower().strip()

    # Define the lists
    vegan_checks = ["vegan", "gemüsebuffet", "salatbuffet", "obst"]
    vegetarian_checks = ["pommes", "gemüsebuffet", "salatbuffet", "obst"]

    # Check matches
    vegan_match = any(check in dish_lower for check in vegan_checks)
    vegetarian_match = any(check in dish_lower for check in vegetarian_checks)

    # Determine the result based on matches
    if vegan_match and vegetarian_match:
        return "vegan"
    elif vegan_match:
        return "vegan"
    elif vegetarian_match:
        return "vegetarian"
    else: 
        # if dish is still not classified, assign label based on menu category
        vegan_menus = ["Auswahlgericht vegan 2", "Tagesmenü vegan"]
        vegetarian_menus = ["Auswahlgericht veget.", "Angebot d. Tages veget.", "Tagesmenü vegetarisch","mensaVital vegetarisch"]

        vegan_match = any(check in menuLine for check in vegan_menus)
        vegetarian_match = any(check in menuLine for check in vegetarian_menus)

        if vegan_match:
            return "vegan"
        elif vegetarian_match:
            return "vegetarian"
        else:  
            return np.nan

