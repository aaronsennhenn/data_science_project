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