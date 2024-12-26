from openai import OpenAI
import os
import nltk
import re
from nltk.corpus import stopwords
import json

OPENAI_KEY = "***REMOVED_OPENAI_KEY***"
os.environ["OPENAI_API_KEY"] = OPENAI_KEY
client = OpenAI()


#Define stop words
nltk.download('stopwords')
stop_words = set(stopwords.words('german'))

#Function to clean text
def preprocess_text(text):
    text = re.sub(r"\[.*?\]", "", text).strip() # remove special characters
    text = text.lower()  # Convert to lowercase
    text = re.sub(r"[^a-zäöüß\s]", "", text)
    text = text.replace("beilage", "").replace("wahl","").replace("mischsalat","").replace("blattsalat","").replace("bunter","")
    text = " ".join(text.split())

    # remove stopwords
    stop_words = set(stopwords.words('german'))  # Replace 'german' with your language of choice
    words = text.split()
    filtered_words = [word for word in words if word.lower() not in stop_words]
    text = " ".join(filtered_words)

    return text.strip()


def ingredient_extraction(df, column):
    ingredients_de_list = []
    ingredients_en_list = []
    tokens_list = []
        
    for menu in df[column]:
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
def embedding_extraction(df,column):

    gpt_embedding_list = []  

    for menu in df[column]:
        if not isinstance(menu, str) or not menu.strip():
            gpt_embedding_list.append(None)
            continue
        cleaned_text = preprocess_text(menu)
    
        # get embedding for each meal
        response = client.embeddings.create(
        input=f"{cleaned_text}",
        model="text-embedding-3-small"
        )
        
        #Trans fom to string and append
        embedding_str = json.dumps(response.data[0].embedding)
        gpt_embedding_list.append(embedding_str)
    
    # Add columns to DataFrame
    df['gpt_embedding'] = gpt_embedding_list
        
    return df

def generate_description(df, column):
    description_en_list = []
    description_de_list = []
    tokens_list = []

    for menu in df[column]:
        # Handle non-string or empty menu values
        if not isinstance(menu, str) or not menu.strip():
            description_en_list.append("No description available.")
            description_de_list.append("Keine Beschreibung verfügbar.")
            tokens_list.append(0)
            continue

        cleaned_text = preprocess_text(menu)

        # Create prompt for English description
        messages_en = [
            {"role": "system", "content": "Provide a short description of the dish in English for someone unfamiliar with it."},
            {"role": "user", "content": f"Describe the dish: '{cleaned_text}'"}
        ]

        # Create prompt for German description
        messages_de = [
            {"role": "system", "content": "Gib eine kurze Beschreibung des Gerichts auf Deutsch für jemanden, der es nicht kennt."},
            {"role": "user", "content": f"Beschreibe das Gericht: '{cleaned_text}'"}
        ]

        # Send request for English description
        completion_en = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages_en,
            max_tokens=100,
            temperature=0.2
        )

        # Send request for German description
        completion_de = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages_de,
            max_tokens=100,
            temperature=0.2
        )

        # Extract descriptions and tokens
        description_en = completion_en.choices[0].message.content.strip()
        description_de = completion_de.choices[0].message.content.strip()
        tokens_used = completion_en.usage.total_tokens + completion_de.usage.total_tokens

        # Append results
        description_en_list.append(description_en)
        description_de_list.append(description_de)
        tokens_list.append(tokens_used)

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
        # Handle non-string or empty menu values
        if not isinstance(menu, str) or not menu.strip():
            taste_en_list.append(None)
            taste_de_list.append(None)
            tokens_list.append(0)
            continue

        cleaned_text = preprocess_text(menu)

        # Create prompt for taste classification
        messages = [
            {"role": "system", "content": "Classify the dish into one of the following categories: Fettig, Leicht, or Süß. Respond with only one word."},
            {"role": "user", "content": f"Classify the dish: '{cleaned_text}'"}
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
        
        #Translat to english
        taste_en = None
        if taste_de == "Fettig":
            taste_en = "Fatty"
        if taste_de == "Leicht":
            taste_en = "Light"
        if taste_de =="Süß":
            taste_en = "Sweet"
                
        #Append results
        taste_de_list.append(taste_de)
        taste_en_list.append(taste_en)
        tokens_list.append(tokens_used)

    # Add results to DataFrame
    df['taste_de'] = taste_de_list
    df['taste_en'] = taste_en_list

    # Handle tokens
    if 'tokens_used' in df.columns:
        df['tokens_used'] = df['tokens_used'] + tokens_list
    else:
        df['tokens_used'] = tokens_list

    return df


def generate_recipe(df, column):
    recipe_en_list = []
    recipe_de_list = []
    tokens_list = []
        
    for dish in df[column]:
        
        # Handle non-string or empty entries in the column
        if not isinstance(dish, str) or not dish.strip():
            recipe_en_list.append("No recipe available.")
            recipe_de_list.append("Kein Rezept verfügbar.")
            tokens_list.append(0)
            continue

        #Create prompt for generating a short recipe
        messages_en = [
            {"role": "system", "content": (
                "You are a professional chef. Create a short and simple recipe for the following dish. "
                "The recipe should include ingredients and step-by-step instructions, written in English, and suitable for a home cook."
            )},
            {"role": "user", "content": f"Please provide a short recipe for the dish: '{dish}'."}
        ]
    
        messages_de = [
            {"role": "system", "content": (
                "Sie sind ein Profikoch. Erstellen Sie ein kurzes und einfaches Rezept für das folgende Gericht. "
                "Das Rezept sollte Zutaten und eine Schritt-für-Schritt-Anleitung enthalten, in deutscher Sprache verfasst und für einen Hausmann geeignet sein."
            )},
            {"role": "user", "content": f"Bitte geben Sie ein kurzes Rezept an für das Gericht: '{dish}'."}
        ]
        
    
    
        #Send request
        completion_en = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages_en,
            max_tokens=200,
            temperature=0.5
        )

        completion_de = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages_de,
            max_tokens=200,
            temperature=0.5
        )

   
        #Extract recipe and tokens used
        recipe_en = completion_en.choices[0].message.content.strip()
        recipe_de = completion_de.choices[0].message.content.strip()
        tokens_used = completion_en.usage.total_tokens + completion_de.usage.total_tokens
        
        # Append to lists
        recipe_en_list.append(recipe_en)
        recipe_de_list.append(recipe_de)
        tokens_list.append(tokens_used)
    
    # Add new columns to DataFrame
    df['recipe_en'] = recipe_en_list
    df['recipe_de'] = recipe_de_list

    # Handle 'tokens_used' column existence
    if 'tokens_used' in df.columns:
        df['tokens_used'] = df['tokens_used'] + tokens_list
    else:
        df['tokens_used'] = tokens_list
        
    return df



## Run all prompts
def run_all_prompts(df, column):
    
    df = ingredient_extraction(df, column)
    df = embedding_extraction(df, column)
    df = generate_recipe(df, column)
    df = generate_description(df, column)
    df = classify_dish_taste(df, column)
    
    return df