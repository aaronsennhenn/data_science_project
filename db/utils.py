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

    return score
