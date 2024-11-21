import pandas as pd
import requests
import re
from datetime import datetime


url_dict = {
    'Cafeteria Wilhelmstraße': 'https://www.my-stuwe.de//wp-json/mealplans/v1/canteens/715?lang=de&v=1731244959433',
    'Cafeteria Morgenstelle': 'https://www.my-stuwe.de//wp-json/mealplans/v1/canteens/724?lang=de&v=1731245000291',
    'Cafeteria und Mensa Prinz Karl': 'https://www.my-stuwe.de//wp-json/mealplans/v1/canteens/623?lang=de&v=1731088441410',
    'Mensa Wilhelmstraße': 'https://www.my-stuwe.de//wp-json/mealplans/v1/canteens/611?lang=de&v=1731088386173',
    'Mensa Morgenstelle': 'https://www.my-stuwe.de//wp-json/mealplans/v1/canteens/621?lang=de&v=1731088361352'
}

file_name = "scraper_results.csv"


def run_scraper(option,date):

    url = url_dict[option]
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    json_data = response.json()
    
    df = pd.json_normalize(json_data)
    match = re.search(r'/canteens/(\d+)', url)
    if not match:
        raise ValueError(f"Unable to extract canteen ID from URL: {url}")
    
    canteen_id = match.group(1)
    if f'{canteen_id}.menus' not in df.columns:
        raise KeyError(f"Column '{canteen_id}.menus' not found in DataFrame")
    
    menus_list = df[f'{canteen_id}.menus'].iloc[0]

    menus_df = pd.DataFrame(menus_list)
    if "photo" in menus_df.columns:
        menus_df.drop(["photo","co2","filtersInclude"], axis=1, inplace=True)
    
    required_columns = ["menuDate", "menuLine", "menu", "studentPrice"]
    for col in required_columns:
        if col not in menus_df.columns:
            menus_df[col] = 'N/A'

    result_df = menus_df[menus_df["menuDate"] == date]

    result_df = result_df.copy()
    result_df["location"] = option

    list_cols = ["menu","meats","icons","allergens","additives"]

    for col in list_cols:
        result_df[col] = result_df[col].apply(lambda x: ', '.join(map(str, x)) if isinstance(x, list) else x)

    return result_df
    

def run_scraper_df(url_dict):
    
    try:
        out_df = pd.read_csv(file_name)
    except:
        out_df = pd.DataFrame(columns=["id","menuLine","studentPrice","guestPrice","pupilPrice","menuDate","menu","meats","icons","allergens","additives","location"])
    
    todays_date = datetime.today().strftime("%Y-%m-%d")

    for _,value in enumerate(url_dict):
        res_df = run_scraper(value,todays_date)
        out_df = pd.concat([out_df,res_df])
    
    out_df.to_csv(file_name, index=False)

if __name__ == "__main__":
    run_scraper_df(url_dict)