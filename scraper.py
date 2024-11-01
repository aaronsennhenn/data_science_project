import pandas as pd
import requests
import re
from datetime import datetime, timedelta


url_dict = {'Wilhelmstraße':'https://www.my-stuwe.de//wp-json/mealplans/v1/canteens/715?lang=de&v=1729619513869',
            'Prinz Karl':'https://www.my-stuwe.de//wp-json/mealplans/v1/canteens/623?lang=de&v=1729614874306',
            'Morgenstelle':'https://www.my-stuwe.de//wp-json/mealplans/v1/canteens/724?lang=de&v=1729621051545'}


def run_scraper(option, date, url=url_dict):

    url = url_dict[option]

    # Make the GET request
    response = requests.get(url)

    # Parse the JSON response
    json_data = response.json()

    # Create and print df
    df = pd.json_normalize(json_data)

    # Extract the list of dictionaries from the column
    match = re.search(r'/canteens/(\d+)', url)

    menus_list = df[match.group(1) + '.menus'].iloc[0]

    # Convert the list of dictionaries into a new DataFrame
    menus_df = pd.DataFrame(menus_list)
    #menus_df.to_excel("test.xlsx")

    menus_df.drop("photo", axis=1, inplace = True)

    return menus_df[menus_df["menuDate"] == date]


def get_dates(num_days):
    today = datetime.today()
    dates = [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(num_days)]
    return dates



