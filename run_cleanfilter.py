"""
This script is responsible for cleaning and improving the icons column in the dishes table which includes filters that are used by the frontend. 
The script is designed to be executed daily at 3:30 AM via a cronjob.

Modules:
- db.db_read load_dishes_table_for_filter_cleaning loads the menu and icon column from the dishes table which are not yet included in the CleanFilters table.
- db.utils correct_icons function corrects the NA icon string rows based on patterns that we found in the data. E.g. if the menu name includes the string "vegan" than the dish is most likely vegan.
- scraper.gpt_prompts classifies all the remaining main course dishes that are still NA into the predefined categories using chatgpt api


Execution:
This script is intended to be run as a cronjob every day at 3:30 AM.
"""


from db.db_read import setup_database_connection
from secret import USER, PASSWORD, HOST, PORT
import pandas as pd
import numpy as np
from scraper.gpt_prompts import classify_missing_filters
from db.db_read import load_dishes_table_for_filter_cleaning
from db.utils import correct_icons
from db.db_write import write_to_filters_clean,FiltersClean,write_to_course,Course



replacement_dict = {
            "F": "fish",
            "G": "poultry",
            "K": "veal",
            "L": "lamb",
            "R": "beef",
            "S": "pork",
            "W": "game",
            "V": "vegetarian"
        }

# replace categories
def replace_categories(icon_string):
    if pd.isna(icon_string):
        return None
    # Split the string into parts, map replacements, and join back
    return ", ".join(replacement_dict.get(part.strip(), part.strip()) for part in icon_string.split(","))


def update_FiltersClean():

    engine, Session = setup_database_connection(USER, PASSWORD, HOST, PORT)

    # load dishes where the icon column in FiltersClean table is not updated yet.
    dish = load_dishes_table_for_filter_cleaning(Session)

    # Stop the function if 'dish' is empty
    if dish.empty:
        return

    dish.replace("NA", np.nan, inplace=True)

    # Apply the function to the DataFrame
    dish["icons"] = dish["icons"].apply(replace_categories)

    # vegan labels tend to be double 'Vegan, vegan'
    dish["icons"] = dish["icons"].apply(lambda x: "vegan" if "vegan" in str(x).lower() else x)

    # correct the missing filters by hand as the dishes belong to one category quite obviously
    dish['icons_clean'] = np.where(
        dish['icons'].isna(),  # Condition: Check where 'icons' is NaN
        dish.apply(lambda row: correct_icons(row['menu'], row['menuLine']), axis=1),  
        dish['icons']  
    )

    # If main dishes are still not classified, retrieve the classification from chatgpt.
    filtered_menu = ["Angebot des Tages", "Auswahlgericht", "Tagesmenü","Auswahlgericht 2"]
    dish.loc[
        dish['icons_clean'].isna() & dish['menuLine'].isin(filtered_menu), 
        'icons_clean'
    ] = dish.loc[
        dish['icons_clean'].isna() & dish['menuLine'].isin(filtered_menu), 
        'menu'
    ].apply(classify_missing_filters)

    with Session() as db_session:
        write_to_filters_clean(dish,engine,db_session)

def update_Course():
    engine, Session = setup_database_connection(USER, PASSWORD, HOST, PORT)
    with Session() as db_session:
        write_to_course(engine,db_session)
    
if __name__ == "__main__":
    update_FiltersClean()
    update_Course()