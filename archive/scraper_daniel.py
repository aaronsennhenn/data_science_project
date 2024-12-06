import pandas as pd
import requests
import re
from datetime import datetime, timedelta
from googletrans import Translator
import re
import numpy as np
from secret import USER, PASSWORD, HOST, PORT
from sqlalchemy import create_engine


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

def get_scraper_df(mensa_name,mensa_day):
    connection_string = f"postgresql+psycopg2://{USER}:{PASSWORD}@{HOST}:{PORT}/postgres"
    engine = create_engine(connection_string)


    # Query the table and load it as a pandas DataFrame
    def query_table_as_dataframe():
        query = "SELECT * from dishes;"  # Replace with your actual table name or SQL query
        df = pd.read_sql(query, engine)
        engine.dispose()
        return df


    # Fetch the data as a DataFrame
    df = query_table_as_dataframe()

    from datetime import date
    dates = [date(2024, 12, 9).strftime("%Y-%m-%d"), date(2024, 12, 10).strftime("%Y-%m-%d"), date(2024, 12, 11).strftime("%Y-%m-%d"),date(2024, 12, 12).strftime("%Y-%m-%d"), date(2024, 12, 13).strftime("%Y-%m-%d")]
    df["menuDate"] = pd.to_datetime(df["menuDate"])
    week_df = df[df["menuDate"].isin(dates)]

    week_df["week_day"] = df['menuDate'].dt.day_name()
    return week_df[(week_df["location"] == mensa_name) & (week_df["week_day"] == mensa_day)]

def get_test_dict():
    # Connection string
    connection_string = f"postgresql+psycopg2://{USER}:{PASSWORD}@{HOST}:{PORT}/postgres"
    engine = create_engine(connection_string)


    # Query the table and load it as a pandas DataFrame
    def query_table_as_dataframe():
        query = "SELECT * from dishes;"  # Replace with your actual table name or SQL query
        df = pd.read_sql(query, engine)
        engine.dispose()
        return df


    # Fetch the data as a DataFrame
    df = query_table_as_dataframe()
    from datetime import date

    ######### The dates are hardcoded here, later on write a function that generates 5 dates of the current weeks' weekdays
    dates = [date(2024, 12, 9).strftime("%Y-%m-%d"), date(2024, 12, 10).strftime("%Y-%m-%d"), date(2024, 12, 11).strftime("%Y-%m-%d"),date(2024, 12, 12).strftime("%Y-%m-%d"), date(2024, 12, 13).strftime("%Y-%m-%d")]
    #########
    
    df["menuDate"] = pd.to_datetime(df["menuDate"])
    week_df = df[df["menuDate"].isin(dates)]
    menu_types = ["Angebot des Tages","Auswahlgericht","Angebot d. Tages veget.","Tagesmenü","Auswahlgericht vegan 2","Auswahlgericht veget.","Aktionsmenü"]
    week_df = week_df[week_df["menuLine"].isin(menu_types)]

    # Initialize empty list for overview_data
    overview_data = []

    # Group the dataframe by 'restaurant_name'
    for location, group in week_df.groupby('location'):
        # Create a dictionary for each restaurant
        restaurant_dict = {
            "name": location,
            "dishes": []
        }

        group.sort_values("menuDate",inplace=True)
        # Iterate over the days of the week (Monday to Friday)
        for date in dates:

            # sort the group by date
            day_dishes = group[group["menuDate"] == date]
                

                # Create a list of dish dictionaries for the day
            dishes_for_day =  [{row["menuLine"]: row["menuGer"]} for _, row in day_dishes.iterrows()]
            #[{row["menuLine"]: row["menuLine"], "menu": row["menuGer"]} for _, row in day_dishes.iterrows()]
            
            # Append the dishes to the restaurant's dish list
            restaurant_dict["dishes"].append(dishes_for_day)
        
        # Append the restaurant dictionary to the overview_data list
        overview_data.append(restaurant_dict)
    return overview_data