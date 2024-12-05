import pandas as pd
import requests
import re
from datetime import datetime, timedelta
from googletrans import Translator
import re
import numpy as np


url_dict = {
    'Cafeteria Wilhelmstraße': 'https://www.my-stuwe.de//wp-json/mealplans/v1/canteens/715?lang=de&v=1731244959433',
    'Cafeteria Morgenstelle': 'https://www.my-stuwe.de//wp-json/mealplans/v1/canteens/724?lang=de&v=1731245000291',
    'Cafeteria und Mensa Prinz Karl': 'https://www.my-stuwe.de//wp-json/mealplans/v1/canteens/623?lang=de&v=1731088441410',
    'Mensa Wilhelmstraße': 'https://www.my-stuwe.de//wp-json/mealplans/v1/canteens/611?lang=de&v=1731088386173',
    'Mensa Morgenstelle': 'https://www.my-stuwe.de//wp-json/mealplans/v1/canteens/621?lang=de&v=1731088361352'
}


def run_scraper(option):

    url = url_dict[option]
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    json_data = response.json()
    df = pd.json_normalize(json_data)
    match = re.search(r'/canteens/(\d+)', url)
    canteen_id = match.group(1)
    menus_list = df[f'{canteen_id}.menus'].iloc[0]

    menus_df = pd.DataFrame(menus_list)

    menus_df.drop(["photo","co2","filtersInclude"], axis=1, inplace=True)
    
    required_columns = ["menuDate", "menuLine", "menu", "studentPrice"]
    for col in required_columns:
        if col not in menus_df.columns:
            menus_df[col] = 'N/A'


    menus_df = menus_df.copy()
    menus_df["location"] = option

    list_cols = ["menu","meats","icons","allergens","additives"]

    for col in list_cols:
        menus_df[col] = menus_df[col].apply(lambda x: ', '.join(map(str, x)) if isinstance(x, list) else x)

    menus_df = menus_df.replace('',np.nan).fillna('NA')

    return menus_df


def get_available_dates():
    today = datetime.today()
    return [
        (today + timedelta(days=i)).strftime("%Y-%m-%d")
        for i in range(8)
        if (today + timedelta(days=i)).weekday() < 5  # weekends
    ]

def translate_text(text, target_language='en'):
    translator = Translator()
    translation = translator.translate(text, dest=target_language)
    return translation.text

def remove_brackets(text):
    # Use a regular expression to find text within brackets
    cleaned_text = re.sub(r'\[.*?\]', '', text)
    # Strip any extra whitespace or trailing commas
    return cleaned_text.strip().strip(',')