"""
This script is responsible for pulling raw data from various canteens and writing the cleaned data into the database table "dishes" for data aggregation and analysis. 
The script is designed to be executed daily at 3:00 AM via a cronjob.

Modules:
- scraper.scraper: Contains the `run_scraper` function to fetch data from the specified URLs.
- scraper.data_transform: Provides functions like `clean_data`, `get_available_dates`, and `remove_brackets` to process and clean the data.
- db.db_write: Includes `setup_database_connection` and `write_to_db` for database operations.
- secret: Contains sensitive information such as database credentials.

Data Flow:
1. Establish a database connection using credentials from the `secret` module.
2. Initialize an empty DataFrame to store the results.
3. Iterate over each canteen URL in `URL_DICT` to fetch and clean data.
4. Filter the cleaned data based on available dates.
5. Remove unnecessary brackets from the menu descriptions.
6. Write the final cleaned DataFrame to the "dishes" table in the database.
7. Print a completion message with the current timestamp.

Key Features:
- The script pulls raw data from canteens and processes it for data aggregation and analysis.
- It ensures that duplicate entries are skipped during the database write operation, as handled by the `write_to_db` function.
- The script is scheduled to run every day at 3:00 AM via a cronjob to ensure daily updates.

URL_DICT:
A dictionary mapping canteen names to their respective data source URLs.

Execution:
This script is intended to be run as a cronjob every day at 3:00 AM.
"""

from scraper.scraper import run_scraper
from scraper.data_transform import clean_data, get_available_dates, remove_brackets
import pandas as pd
from db.db_write import setup_database_connection, write_to_db
from secret import USER, PASSWORD, HOST, PORT

URL_DICT = {
    'Cafeteria Wilhelmstraße': 'https://www.my-stuwe.de//wp-json/mealplans/v1/canteens/715?lang=de&v=1731244959433',
    'Cafeteria Morgenstelle': 'https://www.my-stuwe.de//wp-json/mealplans/v1/canteens/724?lang=de&v=1731245000291',
    'Cafeteria und Mensa Prinz Karl': 'https://www.my-stuwe.de//wp-json/mealplans/v1/canteens/623?lang=de&v=1731088441410',
    'Mensa Wilhelmstraße': 'https://www.my-stuwe.de//wp-json/mealplans/v1/canteens/611?lang=de&v=1731088386173',
    'Mensa Morgenstelle': 'https://www.my-stuwe.de//wp-json/mealplans/v1/canteens/621?lang=de&v=1731088361352'
}

def main():
    engine, Session = setup_database_connection(USER, PASSWORD, HOST, PORT)
    result_df = pd.DataFrame(columns=["menuDate", "menuLine", "menu", "studentPrice", "location"])

    for option in URL_DICT:
        temp_df = run_scraper(option, URL_DICT)
        cleaned_df = clean_data(temp_df, option)
        result_df = pd.concat([result_df, cleaned_df])

    available_dates = get_available_dates()
    filtered_df = result_df[result_df["menuDate"].isin(available_dates)].copy()

    filtered_df["menu"] = filtered_df['menu'].apply(remove_brackets)

    write_to_db(filtered_df, engine, Session)

    print(f"Finished at {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
