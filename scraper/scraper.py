import requests
import pandas as pd
import re
import os
import hashlib
from PIL import Image
import torch
from diffusers import StableDiffusionPipeline
from tqdm import tqdm

import concurrent.futures
import threading

def initialize_pipeline():
    if torch.cuda.is_available():
        device = torch.device("cuda")
        print("Using CUDA device")
        pipeline = StableDiffusionPipeline.from_pretrained(
            "sd-legacy/stable-diffusion-v1-5",
            torch_dtype=torch.float16
        ).to(device)
    elif torch.backends.mps.is_available():
        device = torch.device("mps")
        print("Using MPS device")
        pipeline = StableDiffusionPipeline.from_pretrained(
            "sd-legacy/stable-diffusion-v1-5"
        ).to(device)
    else:
        device = torch.device("cpu")
        print("Using CPU device")
        pipeline = StableDiffusionPipeline.from_pretrained(
            "sd-legacy/stable-diffusion-v1-5",
            torch_dtype=torch.float32
        ).to(device)
    
    pipeline.enable_attention_slicing()
    return pipeline, device
pipeline, device = initialize_pipeline()

def get_image_filename(prompt):
    hash_object = hashlib.md5(prompt.encode())
    return f"{hash_object.hexdigest()}.png"

def generate_image(prompt, filename):
    try:
        num_inference_steps = 20 if device != "cpu" else 10
        with torch.no_grad():
            image = pipeline(
                prompt=prompt,
                num_inference_steps=num_inference_steps,
                guidance_scale=7.0
            ).images[0]
        image.save(filename)
        return filename
    except Exception as e:
        print(f"Error generating image for prompt '{prompt}': {e}")
        return None

def fetch_data(url):
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()

def parse_data(json_data, canteen_id):
    df = pd.json_normalize(json_data)
    menus_list = df[f'{canteen_id}.menus'].iloc[0]
    return pd.DataFrame(menus_list)

def run_scraper(option, url_dict, worker_number):
    url = url_dict[option]
    json_data = fetch_data(url)
    match = re.search(r'/canteens/(\d+)', url)
    canteen_id = match.group(1)
    menus_df = parse_data(json_data, canteen_id)
    
    # Change the image folder to one directory up
    image_folder = os.path.abspath(os.path.join('static', 'generated_images'))

    os.makedirs(image_folder, exist_ok=True)

    # Get the total number of images to be generated
    total_images = len(menus_df)
    print(f"Total images to be generated: {total_images}")

    # Function to process each menu item
    def process_menu(index, row):
        menu = row.get("menu", "")
        if isinstance(menu, list):
            menu = ", ".join(filter(None, menu))
        elif menu is None:
            menu = ""

        if menu and not menu.isspace():
            filename = get_image_filename(menu)
            full_path = os.path.join(image_folder, filename)
            if not os.path.exists(full_path):
                print(f"Worker {worker_number} processing image {index}")
                generate_image(menu, full_path)
            menus_df.at[index, 'image_path'] = filename
        else:
            menus_df.at[index, 'image_path'] = "error.jpg"

    # Use ThreadPoolExecutor to process images in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=worker_number) as executor:
        futures = {executor.submit(process_menu, index, row): index for index, row in menus_df.iterrows()}
        concurrent.futures.wait(futures)

    return menus_df
    return menus_df
