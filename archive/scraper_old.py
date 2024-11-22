import pandas as pd
import requests
import re
from datetime import datetime, timedelta
import torch
from diffusers import StableDiffusionPipeline
from PIL import Image
import os
import hashlib
from googletrans import Translator
import psycopg2
from secret import PASSWORD, USER, HOST, PORT
import traceback
import threading

print(f"CUDA available: {torch.cuda.is_available()}")
print(f"CUDA version: {torch.version.cuda}")
print(f"Device count: {torch.cuda.device_count()}")

def initialize_pipeline():
    if torch.cuda.is_available():
        print("CUDA is available. Using GPU.")
        device = torch.device("cuda")
        pipeline = StableDiffusionPipeline.from_pretrained(
            "stabilityai/stable-diffusion-2-1",
            torch_dtype=torch.float16
        ).to(device)
    elif torch.backends.mps.is_available():
        print("MPS is available. Using Apple Silicon GPU.")
        device = torch.device("mps")
        pipeline = StableDiffusionPipeline.from_pretrained(
            "stabilityai/stable-diffusion-2-1"
        ).to(device)
    else:
        print("No GPU available. Using CPU. This will be slow.")
        device = torch.device("cpu")
        pipeline = StableDiffusionPipeline.from_pretrained(
            "stabilityai/stable-diffusion-2-1",
            torch_dtype=torch.float32
        ).to(device)
    
    pipeline.enable_attention_slicing()
    
    if torch.__version__.startswith("1.13"):
        _ = pipeline("warmup pass", num_inference_steps=1)
    
    print(f"Pipeline device: {pipeline.device}")
    return pipeline, device

pipeline, device = initialize_pipeline()

url_dict = {
    'Cafeteria Wilhelmstraße': 'https://www.my-stuwe.de//wp-json/mealplans/v1/canteens/715?lang=de&v=1731244959433',
    'Cafeteria Morgenstelle': 'https://www.my-stuwe.de//wp-json/mealplans/v1/canteens/724?lang=de&v=1731245000291',
    'Cafeteria und Mensa Prinz Karl': 'https://www.my-stuwe.de//wp-json/mealplans/v1/canteens/623?lang=de&v=1731088441410',
    'Mensa Wilhelmstraße': 'https://www.my-stuwe.de//wp-json/mealplans/v1/canteens/611?lang=de&v=1731088386173',
    'Mensa Morgenstelle': 'https://www.my-stuwe.de//wp-json/mealplans/v1/canteens/621?lang=de&v=1731088361352'
}

def get_image_filename(prompt):
    hash_object = hashlib.md5(prompt.encode())
    return f"{hash_object.hexdigest()}.png"

def generate_image(prompt, filename):
    try:
        print(f"Generating image for prompt: {prompt}")
        print(f"Using device: {device}")
        
        num_inference_steps = 20 if device != "cpu" else 10
        
        with torch.no_grad():
            image = pipeline(
                prompt=prompt,
                num_inference_steps=num_inference_steps,
                guidance_scale=7.0
            ).images[0]
        
        image.save(filename)
        print(f"Image successfully generated and saved: {filename}")
        return True
    except Exception as e:
        print(f"Error generating image for prompt '{prompt}': {str(e)}")
        print(f"Error type: {type(e).__name__}")
        print(f"Error details: {e.args}")
        traceback.print_exc()
        return False

def capitalize_first_letter(text):
    return ' '.join(word.capitalize() for word in text.split())

def generate_image_async(prompt, filename):
    def generate():
        generate_image(prompt, filename)
    thread = threading.Thread(target=generate)
    thread.start()

def translate_text(text, target_language='en'):
    translator = Translator()
    translation = translator.translate(text, dest=target_language)
    return translation.text

def save_to_database(data):
    try:
        # Database connection parameters
        DATABASE = "postgres"
        conn_string = f"host={HOST} dbname={DATABASE} user={USER} password={PASSWORD} port={PORT}"

        # Establish the connection
        conn = psycopg2.connect(conn_string)
        cur = conn.cursor()

        # Insert data into the menu table
        for index, row in data.iterrows():
            cur.execute("""
                INSERT INTO public.menu (id, menuLine, photo, studentPrice, guestPrice, pupilPrice, menuDate, menu, meats, icons, filtersInclude, allergens, additives, co2, image_filename)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (menuDate, menuLine) DO NOTHING
            """, (row['id'], row['menuLine'], row['photo'], row['studentPrice'], row['guestPrice'], row['pupilPrice'], row['menuDate'], row['menu'], row['meats'], row['icons'], row['filtersInclude'], row['allergens'], row['additives'], row['co2'], row['image_filename']))

        # Commit the transaction
        conn.commit()

        # Close the cursor and connection
        cur.close()
        conn.close()
        print("Data saved to the database successfully!")

    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL:", error)

def run_scraper(option, date):
    try:
        print(f"Starting scraper for {option} on {date}")
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
        if not menus_list:
            print(f"No menus found for {option} on {date}")
            return pd.DataFrame(columns=["id", "menuDate", "menuLine", "menu", "studentPrice", "guestPrice", "pupilPrice", "photo", "meats", "icons", "filtersInclude", "allergens", "additives", "co2", "image_filename"])
        
        menus_df = pd.DataFrame(menus_list)
        if "photo" in menus_df.columns:
            menus_df.drop("photo", axis=1, inplace=True)
        
        result_df = menus_df[menus_df["menuDate"] == date]
        if result_df.empty:
            print(f"No menu items found for {option} on {date}")
            return pd.DataFrame(columns=["id", "menuDate", "menuLine", "menu", "studentPrice", "guestPrice", "pupilPrice", "photo", "meats", "icons", "filtersInclude", "allergens", "additives", "co2", "image_filename"])
        
        image_folder = os.path.abspath('static/generated_images')
        os.makedirs(image_folder, exist_ok=True)
        
        for index, row in result_df.iterrows():
            menu = row.get("menu", "")
            menuLine = row.get("menuLine", "")
            
            if isinstance(menu, list):
                menu = ", ".join(filter(None, menu))
            elif menu is None:
                menu = ""

            menu = capitalize_first_letter(menu)
            menuLine = capitalize_first_letter(menuLine)

            # Save original data to the database
            result_df.at[index, 'menu'] = menu
            result_df.at[index, 'menuLine'] = menuLine

            if "Angebot d. Tages" in menuLine:
                result_df.at[index, 'image_filename'] = "coffeeshop.jpg"
                print(f"Debug: Using coffeeshop.jpg for {menuLine} - {menu}")
            elif menu and not menu.isspace():
                filename = get_image_filename(menu)
                full_path = os.path.join(image_folder, filename)
                
                if not os.path.exists(full_path):
                    generate_image_async(menu, full_path)
                
                result_df.at[index, 'image_filename'] = filename
                print(f"Debug: Image for {menu} - Filename: {filename}")
            else:
                result_df.at[index, 'image_filename'] = "error.jpg"
                print(f"Debug: Using error.jpg for empty menu - {menuLine}")

        required_columns = ["id", "menuDate", "menuLine", "menu", "studentPrice", "guestPrice", "pupilPrice", "photo", "meats", "icons", "filtersInclude", "allergens", "additives", "co2", "image_filename"]
        for col in required_columns:
            if col not in result_df.columns:
                result_df[col] = 'N/A'

        print(f"Scraper completed for {option}. Found {len(result_df)} menu items.")
        
        # Save the result to the database
        save_to_database(result_df)
        
        # Translate data for display
        result_df['menuLine'] = result_df['menuLine'].apply(lambda x: translate_text(x))
        result_df['menu'] = result_df['menu'].apply(lambda x: translate_text(x))
        
        return result_df

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from URL for {option}: {e}")
    except (KeyError, ValueError, IndexError) as e:
        print(f"Error processing data for {option}: {e}")
    except Exception as e:
        print(f"Unexpected error in run_scraper for {option}: {e}")
    
    return pd.DataFrame(columns=["id", "menuDate", "menuLine", "menu", "studentPrice", "guestPrice", "pupilPrice", "photo", "meats", "icons", "filtersInclude", "allergens", "additives", "co2", "image_filename"])

def get_available_dates():
    today = datetime.today()
    dates = [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
    filtered_dates = []
    for date_str in dates:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        if date_obj.weekday() < 5:  # 0 is Monday, 6 is Sunday
            formatted_date = date_obj.strftime('%A, %Y-%m-%d')
            filtered_dates.append(formatted_date)

    return filtered_dates

def get_available_mensas():
    return list(url_dict.keys())

def get_dates(num_days):
    today = datetime.today()
    dates = [(today + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(num_days)]
    return dates

if __name__ == "__main__":
    available_dates = get_available_dates()
    available_mensas = get_available_mensas()
    for date in available_dates:
        for mensa in available_mensas:
            run_scraper(mensa, date)