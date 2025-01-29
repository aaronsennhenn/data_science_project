"""
This script contains helper functions that are used by other scripts in the project such as translation, cosine similarity, and price imputation.
"""


from deep_translator import GoogleTranslator
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.linear_model import LinearRegression
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.compose import ColumnTransformer
from pandas.api.types import is_datetime64_any_dtype
from scipy.stats import mode
import warnings
import ast

warnings.simplefilter(action='ignore', category=UserWarning)
warnings.simplefilter(action='ignore', category=pd.errors.SettingWithCopyWarning)


def translate_text_all_capitalized(text: str) -> str:
    """
    Translates a given German text into English and capitalizes the first letter of each word in the translated text.

    Args:
        text (str): The German text to be translated.

    Returns:
        str: The translated text with each word's first letter capitalized.
    """
    translator = GoogleTranslator(source='de', target='en')
    translated_text = translator.translate(text)
    return translated_text.title()

def translate_text_first_word_capitalized(text: str) -> str:
    """
    Translates a given German text into English and capitalizes only the first letter 
    of the first word in the translated text.

    Args:
        text (str): The German text to be translated.

    Returns:
        str: The translated text with only the first word capitalized.
    """
    translator = GoogleTranslator(source='de', target='en')
    translated = translator.translate(text)
    return translated.capitalize()


def compute_cosine_similarity(user_vector_str, dish_embedding_str):
    """
    Computes the cosine similarity between a user vector and a dish embedding.
    Handles input vectors stored as strings in list form.

    Args:
        user_vector_str (str): The vector representing the user's preferences, stored as a string.
        dish_embedding_str (str): The vector representing the dish's embedding, stored as a string.

    Returns:
        float: The cosine similarity score between the user vector and the dish embedding.
    """

    if user_vector_str:

        # Convert string inputs to NumPy arrays. Unfortunatly, we stored the embedding vector as a list in string format. 
        # In hindsight, it would have been better to store it as a json or different data format
        user_vector = np.array(ast.literal_eval(user_vector_str))
        dish_embedding = np.array(ast.literal_eval(dish_embedding_str))

        # Compute cosine similarity
        score = cosine_similarity(user_vector.reshape(1, -1), dish_embedding.reshape(1, -1))[0, 0]

    else:
        # return 0 if user vector is empty
        score = 0

    return round(score,3)

def correct_icons(dish_name: str,menuLine: str) -> str:
    """
    This function is used to clean the icons column that we obtain from scraping the mensa website. Often times it is missing. We correct it by 
    first checking if the dish name contains any of the keywords that are associated with the icons. If not, we use OpenAI to classify the dish into the
    correct category.

    Args:
        dish_name (str): The name of the dish to be classified.
        menuLine (str): The menu category or description associated with the dish.

    Returns:
        str or float: Returns "vegan" if the dish is classified as vegan, "vegetarian" if it is vegetarian,
                      or NaN if it cannot be classified.
    
    """
    if not dish_name:
        return np.nan
    

    dish_lower = str(dish_name).lower().strip()

    # Define the lists
    vegan_checks = ["vegan", "gemüsebuffet", "salatbuffet", "obst"]
    vegetarian_checks = ["pommes", "gemüsebuffet", "salatbuffet", "obst"]

    # Check matches
    vegan_match = any(check in dish_lower for check in vegan_checks)
    vegetarian_match = any(check in dish_lower for check in vegetarian_checks)

    # Determine the result based on matches
    if vegan_match and vegetarian_match:
        return "vegan"
    elif vegan_match:
        return "vegan"
    elif vegetarian_match:
        return "vegetarian"
    else: 
        # if dish is still not classified, assign label based on menu category
        vegan_menus = ["Auswahlgericht vegan 2", "Tagesmenü vegan"]
        vegetarian_menus = ["Auswahlgericht veget.", "Angebot d. Tages veget.", "Tagesmenü vegetarisch","mensaVital vegetarisch"]

        vegan_match = any(check in menuLine for check in vegan_menus)
        vegetarian_match = any(check in menuLine for check in vegetarian_menus)

        if vegan_match:
            return "vegan"
        elif vegetarian_match:
            return "vegetarian"
        else:  
            return np.nan



# functions for missing price prediction. For the regression columns, OLS is applied. For the other columns, majority voting is used to capture the time dependent price.
regression_columns = ["Auswahlgericht",'Auswahlgericht vegan',"Auswahlgericht veget.","Angebot des Tages",'mensaVital vegan','mensaVital','mensaVital vegetarisch']
other_columns = ["Beilagen vorport.","Tagesmenü vegetarisch", 'Tagesmenü vegan', 'Tagesmenü','Dessert vorport.','Salat-/ Gemüsebuffet 100g' ,'Dessert SB','Beilagen SB','Aktionsmenü','Angebot d. Tages veget.',"Angebot d. Tages vegan"]


def impute_with_majority_vote(group, price_column, window=10):
    """
    Imputes missing prices of "other_columns" using majority voting of the most recent prices as no variance is included in those prices.
    """
    # Reset index to ensure proper positional slicing
    group = group.reset_index(drop=True)
    
    # Create a copy of the `studentPrice` column for prediction
    group['price_predicted'] = np.nan  # Initialize as NaN for all rows

    # Iterate over rows where missingPrices == 1
    for idx in group[group['missingPrices'] == 1].index:
        # Get the last `window` non-missing prices before the current index
        recent_prices = group.iloc[:idx][price_column]  # All rows before the current one
        recent_prices = recent_prices[recent_prices > 0].tail(window)  # Take last `window` non-missing prices

        # Calculate the majority vote (mode) from recent prices
        if not recent_prices.empty:
            imputed_value = mode(recent_prices).mode  # Majority vote
        else:
            imputed_value = 0  # Default value if no recent prices exist
        
        # Update only the missing price in `price_predicted`
        group.at[idx, 'price_predicted'] = imputed_value

    return group

def impute_missing_prices(df: pd.DataFrame,price_column: str) -> pd.DataFrame:
    """
    Imputes missing prices in a DataFrame using OLS for menu categories with variance and majority voting for others without variance.

    Args:
        df (pd.DataFrame): The input DataFrame containing menu information, including dates, menu categories, 
                           ingredients, and prices.
        price_column (str): The name of the column containing the prices to be imputed.

    Returns:
        pd.DataFrame: A DataFrame with missing prices imputed, containing both regression-based predictions and 
                      majority-vote-based imputations for different menu categories.
    """

    # Check if 'menuDate' is a datetime column
    if not is_datetime64_any_dtype(df['menuDate']): df['menuDate'] = pd.to_datetime(df['menuDate'])

    # Check if 'icons_clean' column exists
    if 'icons_clean' not in df.columns: df.rename(columns={'icons': 'icons_clean'}, inplace=True)
    df.sort_values("menuDate",inplace=True)

    # add flag if price is missing.
    df['missingPrices'] = ((df[price_column] == 0) | (df[price_column] == -1)).astype(int)

    # Add days since the first date
    df['days'] = (df['menuDate'] - df['menuDate'].min()).dt.days 

    # get regression rows
    regress_df = df[df['menuLine'].isin(regression_columns)]

    # Convert ingredients and menuLine into binary features
    regress_df['icons_clean'] = regress_df['icons_clean'].fillna('')

    # Create a ColumnTransformer to vectorize the 'icons_clean' and 'menuLine' columns
    transformer = ColumnTransformer(
        transformers=[
            ('icons_clean_vectorizer', CountVectorizer(tokenizer=lambda x: x.split(', ')), 'icons_clean'),
            ('menuLine_vectorizer', CountVectorizer(tokenizer=lambda x: [x]), 'menuLine')
        ]
    )

    # fit and transform ColumnTransformer
    ingredient_features = transformer.fit_transform(regress_df).toarray()

    # Convert to numpy arrays
    days_np = regress_df['days'].values.reshape(-1, 1)
    prices_np = regress_df[price_column].values

    # Prepare data for regression
    X_train = np.hstack([
        days_np[regress_df['missingPrices'] == 0],
        ingredient_features[regress_df['missingPrices'] == 0]
    ])
    y_train = prices_np[regress_df['missingPrices'] == 0]

    # Train the Linear Regression model
    model = LinearRegression()
    model.fit(X_train, y_train)

    # Prepare data for prediction
    X_predict = np.hstack([
        days_np[regress_df['missingPrices'] == 1],
        ingredient_features[regress_df['missingPrices'] == 1]
    ])

    # Predict missing prices
    predicted_prices = model.predict(X_predict)

    # Update the DataFrame
    regress_df.loc[regress_df['missingPrices'] == 1, 'price_predicted'] = np.round(predicted_prices,2)  # Add predictions

    # For other Menu Categories with no price variance, impute missing price with majority voting of most recent dishes, to capute the time dependent price.
    majvot_df = df[df['menuLine'].isin(other_columns)]
    majvot_df = majvot_df.groupby('menuLine', group_keys=False).apply(impute_with_majority_vote, price_column)
    

    return pd.concat([regress_df,majvot_df])


def format_price(price):
    """
    Formats a price value for displaying it properly on the menu page

    Args:
        price (float or str): The price value to be formatted. Can be a float or a string.

    Returns:
        str: The formatted price string with a comma as the decimal separator.
             If the input is not a float or string, the original value is returned unchanged.
    """
    if isinstance(price, float):
        return f"{price:,.2f}".replace('.', ',')
    
    if isinstance(price, str):
        return price.replace('.', ',')
    
    return price


def format_price_column(df: pd.DataFrame, price_column: str, price_imputed_column: str) -> pd.DataFrame:
    """
    Formats a price column in a DataFrame, replacing missing prices (indicated by -1) with imputed prices 
    and ensuring the prices are formatted with a comma as the decimal separator.

    Args:
        df (pd.DataFrame): The DataFrame containing the price column and imputed price column.
        price_column (str): The name of the column containing the original prices.
        price_imputed_column (str): The name of the column containing imputed prices to use for missing values.

    Returns:
        pd.DataFrame: The updated DataFrame with the formatted price column.
    """
    formatted_prices = []    
    
    # Check if its -1. Missing prices are stored as -1 by the scraper
    for price, imputed_price in zip(df[price_column], df[price_imputed_column]):
        if price == -1 or (isinstance(price, str) and price.strip() == '-1'):
            price = imputed_price
        
        #Format the price   
        if isinstance(price, float):
            formatted_price = f"{price:,.2f}".replace('.', ',')
        elif isinstance(price, str):
            try:
                formatted_price = price.replace('.', ',')
            except ValueError:
                formatted_price = price
        else:
            formatted_price = price
        
        formatted_prices.append(formatted_price)
        
    # Append to df
    df[price_column] = formatted_prices
            
    return df


def get_month_name(month_number: int, lang='en') -> str:
    """
    Converts a month number to its corresponding month name in the specified language.

    Args:
        month_number (int): The numeric representation of the month (1-12).
        lang (str): The language code for the desired month name

    Returns:
        str: The month name corresponding to the given month number and language.
             Returns "Unknown" if the month number is not between 1 and 12 or the language is not supported.
    """
    
    month_names = {
        'en': {
            1: "January", 2: "February", 3: "March", 4: "April",
            5: "May", 6: "June", 7: "July", 8: "August",
            9: "September", 10: "October", 11: "November", 12: "December"
        },
        'de': {
            1: "Januar", 2: "Februar", 3: "März", 4: "April",
            5: "Mai", 6: "Juni", 7: "Juli", 8: "August",
            9: "September", 10: "Oktober", 11: "November", 12: "Dezember"
        }
    }
    return month_names[lang].get(month_number, "Unknown")