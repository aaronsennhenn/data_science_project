import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import re

def clean_data(menus_df, option):
    menus_df.drop(["photo", "co2", "filtersInclude"], axis=1, inplace=True)
    
    required_columns = ["menuDate", "menuLine", "menu", "studentPrice"]
    for col in required_columns:
        if col not in menus_df.columns:
            menus_df[col] = 'N/A'

    menus_df["location"] = option

    list_cols = ["menu", "meats", "icons", "allergens", "additives"]
    for col in list_cols:
        menus_df[col] = menus_df[col].apply(lambda x: ', '.join(map(str, x)) if isinstance(x, list) else x)

    menus_df = menus_df.replace('', np.nan).fillna('NA')
    return menus_df

def get_available_dates():
    today = datetime.today()
    return [
        (today + timedelta(days=i)).strftime("%Y-%m-%d")
        for i in range(8)
        if (today + timedelta(days=i)).weekday() < 5  # weekdays only
    ]

def remove_brackets(text):
    cleaned_text = re.sub(r'\[.*?\]', '', text)
    return cleaned_text.strip().strip(',')


def collect_unique_meats(data):
    encodings = {"F":"Fisch", "G":"Geflügel", "R":"Rind", "S":"Schwein", "V":"Vegetarisch", "W":"Wild", "L":"Lamm", "K":"Kalb"}
    unique_strings = set()
    
    for item in data:
        for sub_item in item[0].split(','):
            sub_item = sub_item.strip()
            if sub_item != 'NA':
                unique_strings.add(sub_item)
    
    encoded_strings = [(string, encodings[string]) for string in unique_strings if string in encodings]
    return encoded_strings