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

warnings.simplefilter(action='ignore', category=UserWarning)
warnings.simplefilter(action='ignore', category=pd.errors.SettingWithCopyWarning)


def translate_text_all_capitalized(text: str) -> str:
    translator = GoogleTranslator(source='de', target='en')
    translated_text = translator.translate(text)
    return translated_text.title()

def translate_text_first_word_capitalized(text: str) -> str:
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
    # Convert string inputs to NumPy arrays
    user_vector = np.array(eval(user_vector_str))
    dish_embedding = np.array(eval(dish_embedding_str))

    # Compute cosine similarity
    score = cosine_similarity(user_vector.reshape(1, -1), dish_embedding.reshape(1, -1))[0, 0]

    return round(score,3)

def correct_icons(dish_name,menuLine):
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



# functions for missing price prediction
regression_columns = ["Auswahlgericht",'Auswahlgericht vegan',"Auswahlgericht veget.","Angebot des Tages",'mensaVital vegan','mensaVital','mensaVital vegetarisch']
other_columns = ["Beilagen vorport.","Tagesmenü vegetarisch", 'Tagesmenü vegan', 'Tagesmenü','Dessert vorport.','Salat-/ Gemüsebuffet 100g' ,'Dessert SB','Beilagen SB','Aktionsmenü','Angebot d. Tages veget.',"Angebot d. Tages vegan"]




def impute_with_majority_vote(group, price_column, window=10):
    """
    Imputes missing prices in a group by taking the majority vote of the last `window` non-missing prices.
    Only imputes the `price_predicted` column for rows with missing prices.
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

def impute_missing_prices(df,price_column):

    if not is_datetime64_any_dtype(df['menuDate']): df['menuDate'] = pd.to_datetime(df['menuDate'])

    # Check if 'icons_clean' column exists
    if 'icons_clean' not in df.columns: df.rename(columns={'icons': 'icons_clean'}, inplace=True)

    df.sort_values("menuDate",inplace=True)
    # add flag if price is missing.
    df['missingPrices'] = ((df[price_column] == 0) | (df[price_column] == -1)).astype(int)
    df['days'] = (df['menuDate'] - df['menuDate'].min()).dt.days  # Days since the start

    # get regression rows
    regress_df = df[df['menuLine'].isin(regression_columns)]

    # Convert ingredients and menuLine into binary features
    regress_df['icons_clean'] = regress_df['icons_clean'].fillna('') # replace na values with empty string

    transformer = ColumnTransformer(
        transformers=[
            ('icons_clean_vectorizer', CountVectorizer(tokenizer=lambda x: x.split(', ')), 'icons_clean'),
            ('menuLine_vectorizer', CountVectorizer(tokenizer=lambda x: [x]), 'menuLine')
        ]
    )
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

