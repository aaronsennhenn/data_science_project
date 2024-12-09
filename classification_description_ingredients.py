import openai
import json
import requests
from secret import OPENAI_KEY
import pandas as pd

openai.api_key = OPENAI_KEY


##############################################################################

def description_classify_taste(df):

    
    taste_list = []  
    english_description_list = []
    german_description_list = []
    tokens_list = []
        
    for menu in df['menu']:
        
        # Handle non-string or empty entries in the 'menu' column
        if not isinstance(menu, str) or not menu.strip():
            taste_list.append("")
            english_description_list.append("No description available.")
            german_description_list.append("Keine Beschreibung verfügbar.")
            tokens_list.append(0)
            continue
        
        # Create prompt to get category and both English and German descriptions
        messages = [
            {"role": "system", "content": (
                "Classify the dish into one of the following categories: Deftig, Leicht, or Süß. "
                "On line one, respond with only one word: the category. "
                "On line two, provide a short description of the dish in English. "
                "On line three, provide a short description of the dish in German."
            )},
            {"role": "user", "content": (
                f"Classify the dish described as: '{menu}' and give a short description of it in English and German."
            )}
        ]
    
        # Send request using new `openai.ChatCompletion` interface
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=200,
            temperature=0.2
        )
    
        # Extract classification, English description, and German description
        result = response.choices[0].message.content.strip().split("\n")
        taste = result[0].strip() if len(result) > 0 else ""
        english_description = result[1].strip() if len(result) > 1 else ""
        german_description = result[2].strip() if len(result) > 2 else ""
        tokens_used = response.usage.total_tokens
        
        # Append to lists
        taste_list.append(taste)
        english_description_list.append(english_description)
        german_description_list.append(german_description)
        tokens_list.append(tokens_used)
    
    # Add columns to DataFrame
    df['taste'] = taste_list
    df['english_description'] = english_description_list
    df['german_description'] = german_description_list
    df['tokens_used'] = tokens_list
        
    return df

##############################################################################



#############################################################################

def extract_ingredients(df):
    
    #Load the dictionary with all ingredients (Loading robust yet)
    #with open("food_variants", "r", encoding="utf-8") as file:
        #food_variants = json.load(file)
            
    ingredients_list = []
    food_variants = {'pommes': 'pommes', 'schinken': 'schinken', 'kroketten': 'kroketten', 'reis': 'reis', 'couscous': 'couscous', 'käse': 'käse', 'soja': 'soja', 'saiten': 'saiten', 'maultaschen': 'maultaschen', 'tofu': 'tofu', 'ravioli': 'ravioli', 'lachs': 'lachs', 'piccata': 'piccata', 'spätzle': 'spätzle', 'schupfnudeln': 'schupfnudeln', 'weißkraut': 'weißkraut', 'spargel': 'spargel', 'rotkohl': 'rotkohl', 'linsen': 'linsen', 'erbsen': 'erbsen', 'broccoli': 'broccoli', 'kartoffeln': 'kartoffeln', 'pilze': 'pilze', 'karotten': 'karotten', 'salat': 'salat', 'curry': 'curry', 'käsesahnesosse': 'käsesahnesauce', 'käsesahnesoße': 'käsesahnesauce', 'käsesahnesauce': 'käsesahnesauce', 'käsesahne sosse': 'käsesahnesauce', 'käsesahne sauce': 'käsesahnesauce', 'käsesahne soße': 'käsesahnesauce', 'bolognese': 'bolognese', 'teufelssosse': 'teufelsauce', 'teufelsoße': 'teufelsauce', 'teufelssauce': 'teufelsauce', 'teufels sosse': 'teufelsauce', 'teufels sauce': 'teufelsauce', 'teufels soße': 'teufelsauce', 'remoulade': 'remoulade', 'röstzwiebeln': 'röstzwiebeln', 'tomatensosse': 'tomatensauce', 'tomatensoße': 'tomatensauce', 'tomatensauce': 'tomatensauce', 'tomaten sosse': 'tomatensauce', 'tomaten sauce': 'tomatensauce', 'tomaten soße': 'tomatensauce', 'tzatziki': 'tzatziki', 'kräutersosse': 'kräutersauce', 'kräutersoße': 'kräutersauce', 'kräutersauce': 'kräutersauce', 'kräuter sosse': 'kräutersauce', 'kräuter sauce': 'kräutersauce', 'kräuter soße': 'kräutersauce', 'bratensosse': 'bratensauce', 'bratensoße': 'bratensauce', 'bratensauce': 'bratensauce', 'braten sosse': 'bratensauce', 'braten sauce': 'bratensauce', 'braten soße': 'bratensauce', 'rahmsosse': 'rahmsauce', 'rahmsoße': 'rahmsauce', 'rahmsauce': 'rahmsauce', 'rahm sosse': 'rahmsauce', 'rahm sauce': 'rahmsauce', 'rahm soße': 'rahmsauce', 'hollandaise': 'hollandaise', 'kokossosse': 'kokossauce', 'kokossoße': 'kokossauce', 'kokossauce': 'kokossauce', 'kokos sosse': 'kokossauce', 'kokos sauce': 'kokossauce', 'kokos soße': 'kokossauce', 'süß-sauer': 'süß-sauer', 'barbecuesosse': 'barbecuesauce', 'barbecuesoße': 'barbecuesauce', 'barbecuesauce': 'barbecuesauce', 'barbecue sosse': 'barbecuesauce', 'barbecue sauce': 'barbecuesauce', 'barbecue soße': 'barbecuesauce', 'ajvar': 'ajvar', 'kräuter': 'kräuter'}
    
    for menu in df["menu"]:
        #Convert to lowercase
        menu_str = str(menu).lower() if not pd.isna(menu) else ""
        
        #Find all strings
        ingredients = ", ".join(
            {food_variants[variant] for variant in food_variants if variant in menu_str}
        )
        
        #Append list
        ingredients_list.append(ingredients)

    #Add new columne
    df["ingredients"] = ingredients_list
    
    return df

##############################################################################








