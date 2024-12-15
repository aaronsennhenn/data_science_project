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

WORKER_NUMBER = 1

def main():
    engine, Session = setup_database_connection(USER, PASSWORD, HOST, PORT)
    result_df = pd.DataFrame(columns=["menuDate", "menuLine", "menu", "studentPrice", "location", "image_path"])

    for option in URL_DICT:
        temp_df = run_scraper(option, URL_DICT, WORKER_NUMBER)
        cleaned_df = clean_data(temp_df, option)
        result_df = pd.concat([result_df, cleaned_df])

    available_dates = get_available_dates()
    filtered_df = result_df[result_df["menuDate"].isin(available_dates)].copy()

    filtered_df["menu"] = filtered_df['menu'].apply(remove_brackets)

    # placeholders here, need to be filled with the correct values,
    # BUT DONT DO THIS HERE!!!!      
    filtered_df["tokens"] = 0
    filtered_df["tokens"] = filtered_df["tokens"].astype(int)
    filtered_df["menuGer"] = "N/A"
    filtered_df["menuEng"] = "N/A"
    filtered_df["filters"] = "N/A"
    filtered_df["descriptionGer"] = "N/A"
    filtered_df["descriptionEn"] = "N/A"
    filtered_df["taste"] = "N/A"
    filtered_df["ingredients"] = "N/A"

    # Cast columns to the correct data types
    filtered_df = filtered_df.astype({
        'menuDate': 'datetime64[ns]',
        'location': 'string',
        'menuGer': 'string',
        'menuEng': 'string',
        'guestPrice': 'string',
        'studentPrice': 'string',
        'meats': 'string',
        'icons': 'string',
        'filters': 'string',
        'allergens': 'string',
        'additives': 'string',
        'menuLine': 'string',
        'descriptionGer': 'string',
        'descriptionEn': 'string',
        'taste': 'string',
        'ingredients': 'string',
        'image_path': 'string',
    })

    print(filtered_df)

    write_to_db(filtered_df, engine, Session)

    print("Finished")

if __name__ == "__main__":
    main()