"""
These functions will be applied to the filtered_df after scraping. And will written to the dish database table.
"""
import pandas as pd
from openai import OpenAI
from secret import *
import os

#Set up OPENAI
os.environ["OPENAI_API_KEY"] = OPENAI_KEY
client = OpenAI()

def replace_na_meats_and_icons(df, menu_column, meats_column, icon_column):

    # Initialize lists to store updated values
    meats_list = df[meats_column].tolist()  # Initialize with existing values
    icons_list = df[icon_column].tolist()  # Initialize with existing values
    tokens_list = []

    for idx, row in df.iterrows():
        # Check if both meats and icon columns are NA
        if pd.isna(row[meats_column]) and pd.isna(row[icon_column]):
            menu = row[menu_column]

            # Handle non-string or empty entries in the menu column
            if not isinstance(menu, str) or not menu.strip():
                meats_list[idx] = None
                icons_list[idx] = None
                tokens_list.append(0)
                continue

            # GPT prompt for classification
            messages = [
                {"role": "system", "content": (
                    "You are a culinary expert. Based on the dish description provided, classify the dish into one or more of the following categories: "
                    "F: Fish, G: Poultry, K: Calf, L: Lamb, R: Beef, S: Pork, W: Game (wild meat), V: vegetarian, vegan: vegan. "
                    "If the dish contains any meat (F, G, K, L, R, S, W), it cannot be classified as vegetarian (V) or vegan. "
                    "Respond only with the letters or terms, separated by commas, that correspond to the dish type. No additional text."
                )},
                {"role": "user", "content": f"Classify the dish: '{menu}'"}
            ]

            # Send request using the new `openai.ChatCompletion` syntax
            completion = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=50,
                temperature=0.2
            )

            #Extract response and tokens used
            result = completion.choices[0].message.content.strip()
            tokens_used = completion.usage.total_tokens

            #Process result
            categories = [item.strip() for item in result.split(',')]

            #Handle vegetarian or vegan classification
            if 'V' in categories or 'vegan' in categories or 'Vegan' in categories:
                meats_list[idx] = None  
            else:
                meats_list[idx] = result  

            icons_list[idx] = result
            tokens_list.append(tokens_used)
        else:
            #Append zero tokens used for already existing values
            tokens_list.append(0)

    #Update the DataFrame
    df[meats_column] = meats_list
    df[icon_column] = icons_list

    #Handle 'tokens_used' column existence
    if 'tokens_used' in df.columns:
        df['tokens_used'] = df['tokens_used'] + tokens_list
    else:
        df['tokens_used'] = tokens_list

    return df



####Desert SB and Beilagen SB are not calculated with data yet, account for pommes 1,70€

def replace_na_prices(df, category_column, student_price_column, guest_price_column):
    
    prices_median = pd.read_csv("static/csv/prices_median.csv")
    
    merged_df = df.merge(prices_median, on=category_column, how='left', suffixes=('', '_avg'))

    #Replace NaN values
    merged_df[student_price_column] = merged_df[student_price_column].fillna(merged_df['studentPrice_avg'])
    merged_df[guest_price_column] = merged_df[guest_price_column].fillna(merged_df['guestPrice_avg'])

    #Drop the average price columns used for replacement
    merged_df.drop(columns=['studentPrice_avg', 'guestPrice_avg'], inplace=True)
    df = merged_df

    return df
