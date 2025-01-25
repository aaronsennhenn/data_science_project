"""
These functions use the OpenAI API to generete e.g. descriptions, embeddings or recipes from input dish names.
They are soley used in the run_cleanfilter.py script, which itself is regularly executed using a cronjob.
"""

from openai import OpenAI
import os
import nltk
import re
from nltk.corpus import stopwords
import json
from secret import OPENAI_KEY
nltk.download('stopwords')
stop_words = set(stopwords.words('german'))


#Setup OPNEAI Client
os.environ["OPENAI_API_KEY"] = OPENAI_KEY
client = OpenAI()


#Utility function to clean text
def preprocess_text(text):

    text = re.sub(r"\[.*?\]", "", text).strip() # remove special characters
    text = text.lower()  # Convert to lowercase
    text = re.sub(r"[^a-zäöüß\s]", "", text)
    text = text.replace("beilage", "").replace("wahl","").replace("mischsalat","").replace("blattsalat","").replace("bunter","")
    text = " ".join(text.split())

    # remove stopwords
    words = text.split()
    filtered_words = [word for word in words if word.lower() not in stop_words]
    text = " ".join(filtered_words)

    return text.strip()


#Function to extract ingredients
def ingredient_extraction(df, column):
    ingredients_de_list = []
    ingredients_en_list = []
    tokens_list = []
        
    for menu in df[column]:
        try:
            # Handle non-string or empty entries in the 'menu' column
            if not isinstance(menu, str) or not menu.strip():
                ingredients_de_list.append(None)
                ingredients_en_list.append(None)
                tokens_list.append(0)
                continue

            cleaned_text = preprocess_text(menu)
            
            # Create prompt to get dish ingredients in German
            messages_de = [
                {"role": "system", "content": (
                    "Extrahiere die Zutaten aus der folgenden Gerichtsbeschreibung. Berücksichtigen Sie nur Zutaten, die im Text erwähnt werden. Alle Zutaten sollten Substantive und auf Deutsch sein. Geben Sie die Zutaten in Form einer durch Kommata getrennten Liste an."
                )},
                {"role": "user", "content": (
                    f"{cleaned_text}"
                )}
            ]
            
            # Create prompt to get dish ingredients in English
            messages_en = [
                {"role": "system", "content": (
                    "Extract the ingredients from the following dish description. Only consider ingredients that are mentioned in the string. All ingredients should be nouns and in English. Provide the ingredients as a list separated by commas."
                )},
                {"role": "user", "content": (
                    f"{cleaned_text}"
                )}
            ]
            
            # Send request for German ingredients
            completion_de = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages_de,
                max_tokens=200,
                temperature=0.2
            )
            
            # Send request for English ingredients
            completion_en = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages_en,
                max_tokens=200,
                temperature=0.2
            )
            
            # Extract ingredients and tokens used
            ingredients_de = completion_de.choices[0].message.content.strip()
            ingredients_en = completion_en.choices[0].message.content.strip()
            tokens_used = completion_de.usage.total_tokens + completion_en.usage.total_tokens
            
            # Append to lists
            ingredients_de_list.append(ingredients_de)
            ingredients_en_list.append(ingredients_en)
            tokens_list.append(tokens_used)

        except Exception as e:
            # Print the error message and append default values
            print(f"Error in ingredients_extraction for menu item '{menu}': {e}")
            ingredients_de_list.append(None)
            ingredients_en_list.append(None)
            tokens_list.append(0)
    
    # Add columns to DataFrame
    df['ingredients_de'] = ingredients_de_list
    df['ingredients_en'] = ingredients_en_list
    
    # Handle tokens
    if 'tokens_used' in df.columns:
        df['tokens_used'] = df['tokens_used'] + tokens_list
    else:
        df['tokens_used'] = tokens_list
        
    return df



###Gives out strings
def embedding_extraction(df, column):
    """
    This function extracts texts-embeddings from dish names. 
    Beforehand the german stopwords are removed from the dish name string.
    """   
    
    gpt_embedding_list = []  

    for menu in df[column]:
        try:
            if not isinstance(menu, str) or not menu.strip():
                gpt_embedding_list.append(None)
                continue

            cleaned_text = preprocess_text(menu)

            # Get embedding for each meal
            response = client.embeddings.create(
                input=f"{cleaned_text}",
                model="text-embedding-3-small"
            )

            # Transform to string and append
            embedding_str = json.dumps(response.data[0].embedding)
            gpt_embedding_list.append(embedding_str)
            
        except Exception as e: 
            print(f"Error extracting embeddings for menu item '{menu}': {e}")
            gpt_embedding_list.append(None)

    # Add columns to DataFrame
    df['gpt_embedding'] = gpt_embedding_list

    return df


#Descriptions
def generate_description(df, column, menuLine):
    """
    This function generates generates descriptions in english and german language for a given dish. If the dish menuLine happens to be in the dish_filter
    e.g. 'Salat-/ Gemüsebuffet 100g', no description is generated and "No recipe available." is appended instead.
    """     
    
    
    description_en_list = []
    description_de_list = []
    tokens_list = []

    # Define the dish filter
    dish_filter = ['Salat-/ Gemüsebuffet 100g', 'Beilagen vorport.', 'Dessert vorport.', 'Dessert SB', 'Beilagen SB']
        
    for dish, line in zip(df[column], df[menuLine]):
        try:
            # Check if menuLine matches dish_filter or menu is invalid
            if not isinstance(dish, str) or not dish.strip() or line in dish_filter:
                description_en_list.append("No description available.")
                description_de_list.append("Keine Beschreibung verfügbar.")
                tokens_list.append(0)
                continue

            # Create prompt for German description
            messages_de = [
                {"role": "system", "content": (
                    "Du bist ein Student. Gib eine kurze Beschreibung des Gerichts auf Deutsch. "
                    "Verwende einen prägnanten und einfachen Ton. "
                    "Beispiel für das Gericht Chili Con Carne: Ein herzhaftes, würziges Gericht aus Rinderhackfleisch, roten Bohnen, Tomaten, Zwiebeln, Knoblauch und Chili. Gewürzt mit Paprika, Kreuzkümmel und Chili für Schärfe und Geschmack."
                )},
                {"role": "user", "content": f"Beschreibe das Gericht: '{dish}'"}
            ]

            # Send request for German description
            completion_de = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages_de,
                max_tokens=300,
                temperature=0.01
            )

            # Extract descriptions and tokens
            description_de = completion_de.choices[0].message.content.strip()
            tokens_used = completion_de.usage.total_tokens

            # Translate German description into English via follow-up prompt
            translation_prompt = [
                {"role": "system", "content": (
                    "You are an expert translator. Please translate the following German description into clear, natural English. "
                    "Maintain the format and tone, and ensure that the description is easy to understand."
                )},
                {"role": "user", "content": f"Translate this description:\n\n{description_de}"}
            ]

            translation_response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=translation_prompt,
                max_tokens=100,
                temperature=0.2
            )

            description_en = translation_response.choices[0].message.content.strip()
            tokens_used += translation_response.usage.total_tokens

            # Append results
            description_en_list.append(description_en)
            description_de_list.append(description_de)
            tokens_list.append(tokens_used)

        except Exception as e:
            # Print the error message and append default values
            print(f"Error in generate_description for menu item '{dish}': {e}")
            description_en_list.append("No description available.")
            description_de_list.append("Keine Beschreibung verfügbar.")
            tokens_list.append(0)

    # Add results to DataFrame
    df['description_en'] = description_en_list
    df['description_de'] = description_de_list

    # Handle tokens
    if 'tokens_used' in df.columns:
        df['tokens_used'] = df['tokens_used'] + tokens_list
    else:
        df['tokens_used'] = tokens_list

    return df


def classify_dish_taste(df, column):

    taste_en_list = []
    taste_de_list = []
    tokens_list = []

    for menu in df[column]:
        try:
            # Handle non-string or empty menu values
            if not isinstance(menu, str) or not menu.strip():
                taste_en_list.append(None)
                taste_de_list.append(None)
                tokens_list.append(0)
                continue

            # Create prompt for taste classification
            messages = [
                {"role": "system", "content": "Classify the dish into one of the following categories: Fettig, Leicht, or Süß. Respond with only one word."},
                {"role": "user", "content": f"Classify the dish: '{menu}'"}
            ]

            # Send request
            completion = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=10,
                temperature=0.2
            )

            # Extract classification and tokens
            taste_de = completion.choices[0].message.content.strip()
            tokens_used = completion.usage.total_tokens
            
            # Translate to English
            taste_en = None
            if taste_de == "Fettig":
                taste_en = "Fatty"
            elif taste_de == "Leicht":
                taste_en = "Light"
            elif taste_de == "Süß":
                taste_en = "Sweet"
                
            # Append results
            taste_de_list.append(taste_de)
            taste_en_list.append(taste_en)
            tokens_list.append(tokens_used)

        except Exception as e:
            # Print the error message and append default values
            print(f"Error in classify_dish_taste for menu item '{menu}': {e}")
            taste_en_list.append(None)
            taste_de_list.append(None)
            tokens_list.append(0)

    # Add results to DataFrame
    df['taste_de'] = taste_de_list
    df['taste_en'] = taste_en_list

    # Handle tokens
    if 'tokens_used' in df.columns:
        df['tokens_used'] = df['tokens_used'] + tokens_list
    else:
        df['tokens_used'] = tokens_list

    return df


def generate_recipe(df, column, menuLine):   
    """
    This function generates generates recipes in english and german language for a given dish. If the dish menuLine happens to be in the dish_filter
    e.g. 'Salat-/ Gemüsebuffet 100g', no recipe is generated and "No recipe available." is appended instead.
    """    
        
    recipe_en_list = []
    recipe_de_list = []
    tokens_list = []

    # Define the dish filter
    dish_filter = ['Salat-/ Gemüsebuffet 100g', 'Beilagen vorport.', 'Dessert vorport.', 'Dessert SB', 'Beilagen SB']
        
    for dish, line in zip(df[column], df[menuLine]):
        try:
            # Check if menuLine matches dish_filter or dish is invalid
            if not isinstance(dish, str) or not dish.strip() or line in dish_filter:
                recipe_en_list.append("No recipe available.")
                recipe_de_list.append("Kein Rezept verfügbar.")
                tokens_list.append(0)
                continue

            # Create prompt for generating a short recipe in German
            messages_de = [
                {"role": "system", "content": (
                   "Sie sind ein Profikoch. Erstellen Sie ein kurzes und einfaches Rezept für das folgende Gericht. "
                   "Das Rezept sollte Zutaten und eine Schritt-für-Schritt-Anleitung enthalten, in deutscher Sprache verfasst und für einen Hausmann geeignet sein. "
                   "Formatieren Sie das Rezept wie folgt: "
                   "Zutaten:\n- [Zutat 1]\n- [Zutat 2]\n\nAnleitung:\n1. [Schritt 1]\n2. [Schritt 2] "
                   "Stellen Sie sicher, dass die Zutaten und Anweisungen vollständig und klar sind, ohne mitten im Satz abzubrechen."
                   "Vermeiden Sie abschließende Bemerkungen wie 'Guten Appetit'. Geben Sie nur das Rezept an."
                )},
                {"role": "user", "content": f"Bitte geben Sie ein kurzes Rezept an für das Gericht: '{dish}'."}
            ]

            completion_de = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages_de,
                max_tokens=500,
                temperature=0.1
            )

            # Extract the German recipe and token usage
            recipe_de = completion_de.choices[0].message.content.strip()
            tokens_used = completion_de.usage.total_tokens

            # Translate German recipe into English via follow-up prompt
            translation_prompt = [
                {"role": "system", "content": (
                    "You are an expert translator. Please translate the following German recipe into clear, natural English. "
                    "Maintain the format and tone, and ensure that the instructions are easy to follow."
                )},
                {"role": "user", "content": f"Translate this recipe:\n\n{recipe_de}"}
            ]

            translation_response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=translation_prompt,
                max_tokens=500,
                temperature=0.1
            )

            recipe_en = translation_response.choices[0].message.content.strip()
            tokens_used += translation_response.usage.total_tokens

            # Append to lists
            recipe_en_list.append(recipe_en)
            recipe_de_list.append(recipe_de)
            tokens_list.append(tokens_used)

        except Exception as e:
            # Print the error message and append default values
            print(f"Error in generate_recipe for menu item '{dish}': {e}")
            recipe_en_list.append("No recipe available.")
            recipe_de_list.append("Kein Rezept verfügbar.")
            tokens_list.append(0)
    
    # Add new columns to DataFrame
    df['recipe_en'] = recipe_en_list
    df['recipe_de'] = recipe_de_list

    # Handle 'tokens_used' column existence
    if 'tokens_used' in df.columns:
        df['tokens_used'] = df['tokens_used'] + tokens_list
    else:
        df['tokens_used'] = tokens_list
        
    return df


def classify_missing_filters(dish_name):
    """
    This function classifies the dish into the predefined filter categories. It is only applied to those main dishes, where the mensa website information is lacking and where our correction does not work
    No need to run this function in the 'all_prompts' function.
    """
    
    # Create prompt to classify missing filter category
    messages = [
        {"role": "system", "content": (
            "The string that I provide is a dish name. Please classify the dish into one of the following categories: vegan, vegetarian, fish, poultry, veal, lamb, beef, pork, game. Only return the classification string"
        )},
        {"role": "user", "content": (
            f"{dish_name}"
        )}
    ]

    # Send request using new `openai.ChatCompletion` interface
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        max_tokens=200,
        temperature=0.2
    )

    # Extract ingredients and tokens used
    result = completion.choices[0].message.content.strip().split("\n")
    result_string = result[0].strip() if len(result) > 0 else ""

    return result_string  
