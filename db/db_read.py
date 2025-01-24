from sqlalchemy.orm import Session
from .db_write import Dish, Directory, setup_database_connection, User, Rating, Course, Description, Recipe, Embedding, FiltersClean, DishEng, Taste, Ingredient, DishHistory,PriceClean,EmbeddingCluster
from typing import List
from sqlalchemy import func
import datetime
import pandas as pd
from sqlalchemy import or_,func,select,desc,select, union, and_, not_, extract
from typing import List, Tuple
from db.utils import compute_cosine_similarity, get_month_name
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict



def convert_dblist_to_df(db_list):
    dict_list = [vars(obj) for obj in db_list]
    for dictionary in dict_list:
        dictionary.pop('_sa_instance_state', None)
    df = pd.DataFrame(dict_list)        
    return df
        
def get_user_by_username(session: Session, username: str):
    return session.query(User).filter_by(username=username).first()


def get_all_dishes(session: Session) -> List[Dish]:
    return session.query(Dish).all()

def get_average_ratings(db_session, user_name=None):

    # Query the database
    query = db_session.query(
        FiltersClean.icons_clean,
        Rating.rating
    ).join(Rating, FiltersClean.menu_id == Rating.menu_id)

    if user_name:
        query = query.filter(Rating.user_name == user_name)

    raw_ratings = query.all()

    # Process the results to handle multiple categories
    category_ratings = defaultdict(list)

    for icons, rating in raw_ratings:
        # Split the icons_clean field by ", " and assign the rating to each category
        categories = icons.split(", ")
        for category in categories:
            category_ratings[category].append(rating)

    # Compute the average rating for each category
    average_ratings = {
        category: sum(ratings) / len(ratings) for category, ratings in category_ratings.items()
    }

    return average_ratings

def get_dishes_by_date_location_filtered(db_session, date, mensa_name, selected_diet_meat, selected_lang):

    if mensa_name == "all":
        query = db_session.query(Dish).filter(Dish.menuDate == date, Dish.menu != "NA")
    else:
        query = db_session.query(Dish).filter(Dish.menuDate == date, Dish.location == mensa_name, Dish.menu != "NA")


    # join icons_clean for filtering
    query = query.outerjoin(FiltersClean, Dish.id == FiltersClean.menu_id).add_columns(FiltersClean.icons_clean.label("icons_clean"))

    # if user filters by meat or diet, apply filters on icons_clean column
    if selected_diet_meat:
        filters = [FiltersClean.icons_clean.ilike(f"%{icon}%") for icon in selected_diet_meat]
        query = query.filter(or_(*filters))


    # Join additional tables and add columns
    query = (
        query
        .outerjoin(Recipe, Dish.id == Recipe.menu_id)
        .outerjoin(Description, Dish.id == Description.menu_id)
        .outerjoin(DishEng, Dish.id == DishEng.menu_id)
        .outerjoin(Course, Dish.id == Course.menu_id)
        .add_columns(
            # German columns
            Recipe.recipe_de,
            Description.description_de,
            Course.course,
            
            # English columns (conditionally included)
            DishEng.menuLineEng if selected_lang == "en" else None,
            DishEng.menuEng if selected_lang == "en" else None,
            Description.description_en if selected_lang == "en" else None,
            Recipe.recipe_en if selected_lang == "en" else None,
            Course.course_eng if selected_lang == "en" else None,

        )
    )

    
    # join the embedding column to the filtered dataframe
    query = query.outerjoin(Embedding, Dish.id == Embedding.menu_id).add_columns(Embedding.embedding)

    # Compute average rating for menu_ids in the query
    avg_rating_subquery = (
        db_session.query(
            Rating.menu_id.label("menu_id"),
            func.round(func.avg(Rating.rating),2).label("average_rating"),
            func.count(Rating.rating).label("rating_count")  # Count of ratings

        )
        .group_by(Rating.menu_id)
        .subquery()
    )

    # Join the average rating to the main query
    query = query.outerjoin(avg_rating_subquery, Dish.id == avg_rating_subquery.c.menu_id).add_columns(
        avg_rating_subquery.c.average_rating.label("average_rating"),
        avg_rating_subquery.c.rating_count.label("rating_count")

    )

    query = query.outerjoin(PriceClean, Dish.id == PriceClean.menu_id).add_columns(PriceClean.studentPrice_imputed,PriceClean.guestPrice_imputed)

    return query.all()

def get_random_dishes(selected_date, lang, user_name, db_session: Session):
    

    # Query one random main dish that has not been rated by the user yet and is not on the selected date
    if lang == "de":
        query = (
            select(Dish.id, Dish.menu, Dish.studentPrice,Dish.guestPrice)
            .outerjoin(Rating, (Dish.id == Rating.menu_id) & (Rating.user_name == user_name))
            .outerjoin(Course, Course.menu_id == Dish.id)
            .where(Rating.menu_id == None,
                Dish.menuDate != selected_date,
                Course.course == "Hauptspeise",
                Dish.menu != "NA",
                Dish.studentPrice > 0,
                Dish.guestPrice > 0
            )
            .order_by(func.random())
            .limit(1)  # Limit to 1 random dish
        )
    else:
        query = (
            select(DishEng.menu_id, DishEng.menuEng,Dish.studentPrice,Dish.guestPrice)
            .outerjoin(Dish, Dish.id == DishEng.menu_id)
            .outerjoin(Rating, (DishEng.menu_id == Rating.menu_id) & (Rating.user_name == user_name))
            .outerjoin(Course, Course.menu_id == DishEng.menu_id)
            .where(Rating.menu_id == None,
                DishEng.menuDate != selected_date,
                Course.course_eng == "Main Dish",
                DishEng.menuEng != "N/a",
                Dish.studentPrice > 0,
                Dish.guestPrice > 0
            )
            .order_by(func.random())
            .limit(1)  # Limit to 1 random dish
        )

    # Execute the query
    result = db_session.execute(query).fetchone()
    return result


def get_image_path(dish_id: int, session: Session) -> str:
    dish = session.query(Dish).filter_by(id=dish_id).first()
    return dish.image_path if dish else None

def get_user_vector(username: str, session: Session) -> List[float]:
    user = session.query(User).filter_by(username=username).first()
    return user.user_vector if user else None

def get_meat_options(session: Session) -> List[str]:
    return session.query(Dish.meats).distinct().all()

def get_course_eng(session: Session, date, menuline, menu, location) -> str:
    course = session.query(Course.course_eng).filter(
        Course.menuDate == date,
        Course.menuLine == menuline,
        Course.menu == menu,
        Course.location == location
    ).first()
    return course[0] if course else None

def get_course(session: Session, date, menuline, menu, location) -> str:
    course = session.query(Course.course).filter(
        Course.menuDate == date,
        Course.menuLine == menuline,
        Course.menu == menu,
        Course.location == location
    ).first()
    return course[0] if course else None

    
def load_dishes_table_for_filter_cleaning(Session, update_table):
    if update_table == "FiltersClean":
        table = FiltersClean
    elif update_table == "Embedding":
        table = Embedding
    elif update_table == "Description":
        table = Description
    elif update_table == "Taste":
        table = Taste
    elif update_table == "Recipe":
        table = Recipe
    elif update_table == "Ingredient":
        table = Ingredient


    with Session() as session:
        # Query for dishes not in update_table
        dishes = session.query(
            Dish.id,
            Dish.menuLine,
            Dish.menu,
            Dish.icons
        ).filter(
            ~session.query(table).filter(table.menu_id == Dish.id).exists()
        ).all()

        # Convert results to a list of dictionaries
        data = [
            {
                'id': dish.id,
                'menuLine': dish.menuLine,
                'menu': dish.menu,
                'icons': dish.icons
            }
            for dish in dishes
        ]
        
        # Return as a DataFrame
        return pd.DataFrame(data)


from datetime import datetime, timedelta

def get_next_five_days_data(session: Session) -> dict:
    today = datetime.now().date()
    date_range = [today + timedelta(days=x) for x in range(5)]

    # MANUALLY FIX DATES OVER CHRISTMAS PERIOD BECAUSE MENSA IS CLOSED. MUST BE REMOVED AFTER CHRISTMAS
    #date_range = [datetime(2024, 12, 17), datetime(2024, 12, 18), datetime(2024, 12, 19), datetime(2024, 12, 20)]
    
    results = {}
    for date in date_range:
        dishes = session.query(Dish).filter_by(menuDate=date).all()
        locations = list(set(dish.location for dish in dishes))
        results[date.strftime('%A, %Y-%m-%d')] = locations
    
    return results

def get_unique_mensas(session: Session) -> List[str]:
    return [mensa.location for mensa in session.query(Dish.location).distinct()]

# Get total number of mensas (Dish.location)
def get_total_mensas(session: Session) -> int:
    return session.query(Dish.location).distinct().count()

# Get total number of ratings (table rating)
def get_total_ratings(session: Session) -> int:
    return session.query(Rating.id).distinct().count()

# Get total number of menus (table menu)
def get_total_menus(session: Session) -> int:
    return session.query(Dish.id).distinct().count()

# Get list of available mensas (Dish.location)
def get_available_mensas(session: Session) -> List[str]:
    return [mensa.location for mensa in session.query(Dish.location).distinct()]

# Get time window since when the Dish was last updated which can be seen in menuDate
def get_first_updated_date(session: Session) -> datetime:
    return session.query(Dish.menuDate).order_by(Dish.menuDate.asc()).first()[0]

# Get unique menu lines to sort menus into Main, Side dish or Dessert
def get_unique_menu_lines(session: Session, date: str, location: str) -> List[str]:
    dishes = session.query(Dish).filter_by(menuDate=date, location=location).all()
    unique_menu_lines = list(set(dish.menuLine for dish in dishes if dish.menuLine))
    return unique_menu_lines

# Get number of dishes (Dish.menu) per each mensa (Dish.location)
def get_dish_count_per_mensa(session: Session) -> dict:
    results = {}
    for mensa in get_available_mensas(session):
        count = session.query(Dish).filter_by(location=mensa).count()
        results[mensa] = count
    return results

#Get average prices per menu line (Dish.menuLine)
def get_average_prices_per_menuline(session: Session) -> dict:
    results = {}
    menu_lines = session.query(Dish.menuLine).distinct().all()
    
    for menu_line in menu_lines:
        menu_line = menu_line[0]  # Extract string from tuple
        avg_prices = session.query(
            func.avg(Dish.pupilPrice).label('avg_pupil'),
            func.avg(Dish.studentPrice).label('avg_student'),
            func.avg(Dish.guestPrice).label('avg_guest')
        ).filter(Dish.menuLine == menu_line).first()
        
        results[menu_line] = {
            'pupil': round(avg_prices.avg_pupil, 2) if avg_prices.avg_pupil else 0,
            'student': round(avg_prices.avg_student, 2) if avg_prices.avg_student else 0,
            'guest': round(avg_prices.avg_guest, 2) if avg_prices.avg_guest else 0
        }
    
    return results

# Get lowest prices per menu line (Dish.menuLine)
def get_lowest_prices_per_menuline(session: Session) -> dict:
    results = {}
    menu_lines = session.query(Dish.menuLine).distinct().all()
    
    for menu_line in menu_lines:
        menu_line = menu_line[0]
        min_prices = session.query(
            func.min(Dish.pupilPrice).label('min_pupil'),
            func.min(Dish.studentPrice).label('min_student'),
            func.min(Dish.guestPrice).label('min_guest')
        ).filter(Dish.menuLine == menu_line).first()
        
        results[menu_line] = {
            'pupil': round(min_prices.min_pupil, 2) if min_prices.min_pupil else 0,
            'student': round(min_prices.min_student, 2) if min_prices.min_student else 0,
            'guest': round(min_prices.min_guest, 2) if min_prices.min_guest else 0
        }
    
    return results

# Get average Menu Prices per Each Mensa (Dish.menu) over all prices (Dish.pupilPrice Dish.studentPrice and Dish.guestPrice) but grouped by each menu line (Dish.menuLine)
def get_average_prices_per_menuline_per_mensa(session: Session) -> dict:
    results = {}
    for mensa in get_available_mensas(session):
        menu_lines = session.query(Dish.menuLine).filter_by(location=mensa).distinct().all()
        results[mensa] = {}
        
        for menu_line in menu_lines:
            menu_line = menu_line[0]
            avg_price = session.query(
                func.avg((Dish.pupilPrice + Dish.studentPrice + Dish.guestPrice) / 3)
            ).filter(Dish.location == mensa, Dish.menuLine == menu_line).scalar()
            
            results[mensa][menu_line] = round(avg_price, 2) if avg_price else 0
    return results

# Get lowest Menu Prices per Each Mensa (Dish.menu) over all prices (Dish.pupilPrice Dish.studentPrice and Dish.guestPrice) but grouped by each menu line (Dish.menuLine)
def get_lowest_prices_per_menuline_per_mensa(session: Session) -> dict:
    results = {}
    for mensa in get_available_mensas(session):
        menu_lines = session.query(Dish.menuLine).filter_by(location=mensa).distinct().order_by(Dish.menuLine).all()
        results[mensa] = {}
        
        for menu_line in menu_lines:
            menu_line = menu_line[0]
            lowest_price = session.query(
                func.min((Dish.pupilPrice + Dish.studentPrice + Dish.guestPrice) / 3)
            ).filter(Dish.location == mensa, Dish.menuLine == menu_line).scalar()
            
            results[mensa][menu_line] = round(lowest_price, 2) if lowest_price else 0
    return results

# Get menu and menu line and price of lowest price dish per each mensa (Dish.location)
def get_menu_with_lowest_price(session: Session) -> dict:
    results = {}
    for mensa in get_available_mensas(session):
        lowest_price_dish = session.query(
            Dish.menu,
            Dish.menuLine,
            Dish.pupilPrice,
            Dish.studentPrice,
            Dish.guestPrice,
            ((Dish.pupilPrice + Dish.studentPrice + Dish.guestPrice) / 3).label('avg_price')
        ).filter_by(location=mensa
        ).order_by(func.coalesce(((Dish.pupilPrice + Dish.studentPrice + Dish.guestPrice) / 3), float('inf'))
        ).first()
        
        if lowest_price_dish:
            results[mensa] = {
                'menu': lowest_price_dish.menu,
                'menu_line': lowest_price_dish.menuLine,
                'pupilPrice': lowest_price_dish.pupilPrice,
                'studentPrice': lowest_price_dish.studentPrice,
                'guestPrice': lowest_price_dish.guestPrice,
                'avg_price': lowest_price_dish.avg_price
            }
        else:
            results[mensa] = None
    return results

# Get price development per menu line (Dish.menuLine)
def get_price_development(session: Session) -> dict:
    menu_lines = session.query(Dish.menuLine).distinct().all()
    price_data = {}
    
    for menu_line in menu_lines:
        menu_line = menu_line[0]
        prices = session.query(
            Dish.menuDate,
            Dish.pupilPrice,
            Dish.studentPrice,
            Dish.guestPrice
        ).filter(Dish.menuLine == menu_line).order_by(Dish.menuDate).all()
        
        price_data[menu_line] = {
            'dates': [p.menuDate for p in prices],
            'pupil_prices': [p.pupilPrice for p in prices],
            'student_prices': [p.studentPrice for p in prices],
            'guest_prices': [p.guestPrice for p in prices]
        }
    
    return price_data

# Get district count of menu line (Dish.menuLine) per each mensa (Dish.location) (such that with this information I can plot pie charts)
def get_menu_line_distribution(session: Session) -> dict:
    results = {}
    today = datetime.now().date()
    week_end = today + timedelta(days=7)
    
    for mensa in get_available_mensas(session):
        menu_line_counts = session.query(
            Dish.menuLine, 
            func.count(Dish.menuLine)
        ).filter(
            Dish.location == mensa,
            Dish.menuDate >= today,
            Dish.menuDate < week_end
        ).group_by(Dish.menuLine).all()
        
        results[mensa] = {menu_line: count for menu_line, count in menu_line_counts}
    
    return results

# Get directory values of additives and allergens 
def get_written_forms(session):
    additives_dict = {}
    additives_dict_eng = {}
    allergens_dict = {}
    allergens_dict_eng = {}
    meats_dict = {}
    meats_dict_eng = {}
    
    directory_entries = session.query(Directory).all()
    
    for entry in directory_entries:
        if entry.additives:
            additives_dict[entry.additives] = entry.additives_written
            additives_dict_eng[entry.additives] = entry.additives_written_eng
        if entry.allergens:
            allergens_dict[entry.allergens] = entry.allergens_written
            allergens_dict_eng[entry.allergens] = entry.allergens_written_eng
        if entry.meats:
                meats_dict[entry.meats] = entry.meats_written
                meats_dict_eng[entry.meats] = entry.meats_written_eng
            
    return additives_dict, additives_dict_eng, allergens_dict, allergens_dict_eng, meats_dict, meats_dict_eng


def get_user_name(db_session, username):
    return db_session.query(User).filter_by(username=username).first()

# Get descritoptions de and en based on menu_id and the corresponding description_de and description_en
def get_descriptions(db_session):
    descriptions = {}
    description_entries = db_session.query(Description).all()
    for entry in description_entries:
        descriptions[entry.menu_id] = {
            'description_de': entry.description_de,
            'description_en': entry.description_en
        }
    return descriptions

# Get recipes de and en based on menu_id and the corresponding recipe_de and recipe_en
def get_recipes(db_session):
    recipes = {}
    recipe_entries = db_session.query(Recipe).all()
    for entry in recipe_entries:
        recipes[entry.menu_id] = {
            'recipe_de': entry.recipe_de,
            'recipe_en': entry.recipe_en
        }
    return recipes


def get_ratings_of_the_week(session: Session, week_dates: List[str]) -> List[Rating]:
    query = session.query(
        func.avg(Rating.rating).label('avg_rating'),
        func.count(Rating.id).label('rating_count'),
        Dish.location,
        Dish.menu,
        Dish.menuDate
        ).join(Dish, Rating.menu_id == Dish.id
        ).filter(Dish.menuDate.in_(week_dates)
        ).group_by(Dish.id,Dish.location,Dish.menuDate).all()

    result = [
        {
            'location': rating.location,
            'menu': rating.menu,
            'menuDate': rating.menuDate,
            'avg_rating': round(rating.avg_rating, 2),
            'rating_count': rating.rating_count
        } for rating in query
    ]
    return pd.DataFrame(result)

def get_top_three_dishes(session: Session, lang):
    
    week_dates = get_weekday_dates()

    # get dishes for the week
    top_dishes = session.query(
        Dish.menu,
        DishEng.menuEng,
        func.avg(Rating.rating).label('avg_rating'),
        func.count(Rating.id).label('rating_count')
        ).filter(
        Dish.menuDate.in_(week_dates),
        Dish.menu != "NA",
        Course.course == "Hauptspeise"
        ).join(Rating, Dish.id == Rating.menu_id
        ).join(Course, Dish.id == Course.menu_id
        ).join(DishEng, Dish.id == DishEng.menu_id
        ).group_by(Dish.id,Dish.menu,DishEng.menuEng
        ).order_by(func.avg(Rating.rating).desc()
        ).limit(3).all()
    
        # Format result
    result = [
        {
            'dish_name': dish.menu if lang == 'de' else dish.menuEng,
            'avg_rating': round(dish.avg_rating, 2),
            'rating_count': dish.rating_count
        } for dish in top_dishes
    ]

    return result

#Get top three mensas of the week (ranked best first) - on y-axis the rating average and on x-axis the location (mensa)
def get_top_three_mensas(session: Session):

    week_dates = get_weekday_dates()

    # get dishes for the week
    top_dishes = session.query(
        Dish.location,
        func.avg(Rating.rating).label('avg_rating'),
        func.count(Rating.id).label('rating_count')
        ).filter(
        Dish.menuDate.in_(week_dates),
        Dish.menu != "NA",
        Course.course == "Hauptspeise"
        ).join(Rating, Dish.id == Rating.menu_id
        ).join(Course, Dish.id == Course.menu_id
        ).group_by(Dish.location
        ).order_by(func.avg(Rating.rating).desc()
        ).limit(3).all()
    
        # Format result
    result = [
        {
            'location': dish.location,
            'avg_rating': round(dish.avg_rating, 2),
            'rating_count': dish.rating_count
        } for dish in top_dishes
    ]

    return result


def get_dishes_and_rating_by_week(db_session: Session, week_dates: List[str]):
    query = db_session.query(
        Dish.menu,
        Dish.id,
        Rating.rating,
        Dish.location
        ).join(Rating, Dish.id == Rating.menu_id
        ).filter(Dish.menuDate.in_(week_dates), Dish.menu != "NA",Rating.rating != None
        ).all()
    
    result = [
        {
            'menu_id': dish.id,
            'menu': dish.menu,
            'rating': dish.rating,
            'location': dish.location
        } for dish in query
    ]
    return pd.DataFrame(result)

# Get total number of ratings a user submitted
def get_total_ratings_by_user(session: Session, username: str) -> int:
    return session.query(func.count(Rating.id)).filter(Rating.user_name == username).scalar()

# Get date of first rating of user
def get_first_rating_date_of_user(session: Session, username: str) -> str:
    first_rating = session.query(func.min(Rating.timestamp)).filter(Rating.user_name == username).scalar()
    if first_rating:
        return first_rating.strftime('%Y-%m-%d')
    return None

# Get favorite dishes (top 3) of user over entire period
def get_favorite_dishes_of_user(session: Session, username: str, lang: str = 'en', limit: int = 3) -> List[Tuple[str, float]]:
    favorite_dishes = session.query(
        Dish.id,
        Dish.menu,
        DishEng.menuEng,
        func.avg(Rating.rating).label('avg_rating')
    ).join(Rating, Dish.id == Rating.menu_id
    ).outerjoin(DishEng, Dish.id == DishEng.menu_id
    ).filter(Rating.user_name == username
    ).group_by(Dish.id, Dish.menu, DishEng.menuEng
    ).order_by(func.avg(Rating.rating).desc()
    ).limit(limit).all()

    return [(dish.menuEng if lang == 'en' and dish.menuEng else dish.menu, round(dish.avg_rating, 2)) for dish in favorite_dishes]

def get_dishes_of_user(session: Session, username: str):
    rated_dishes = session.query(
        Dish.id,
        Dish.menu,
        DishEng.menuEng,
        Rating.rating
    ).join(Rating, Dish.id == Rating.menu_id
    ).outerjoin(DishEng, Dish.id == DishEng.menu_id
    ).filter(Rating.user_name == username
    ).order_by(Rating.rating.desc()
    ).all()

    menu_list = [{"menu_id": item[0],"menu":item[1],"menuEng": item[2], "rating": item[3]} for item in rated_dishes]

    return menu_list

# Get favorite mensas (top 3) of user over entire period
def get_favorite_mensas_of_user(session: Session, username: str, lang: str = 'en', limit: int = 3) -> List[Tuple[str, float]]:
    favorite_mensas = session.query(
        Dish.location,
        DishEng.locationEng,
        func.avg(Rating.rating).label('avg_rating')
    ).join(Rating, Dish.id == Rating.menu_id
    ).outerjoin(DishEng, Dish.id == DishEng.menu_id
    ).filter(Rating.user_name == username
    ).group_by(Dish.location, DishEng.locationEng
    ).order_by(func.avg(Rating.rating).desc()
    ).limit(limit).all()

    return [(mensa.locationEng if lang == 'en' and mensa.locationEng else mensa.location, round(mensa.avg_rating, 2)) for mensa in favorite_mensas]

def get_dishes_history(db_session):

    dishes = db_session.query(DishHistory).all()
    df = convert_dblist_to_df(dishes)
    df['menuDate'] = pd.to_datetime(df['menuDate'],format='%Y-%m-%d')


    return df

def get_combined_dishes(db_session: Session):
    """
    Combine all rows from DishHistory and rows from Dish not in DishHistory.
    Return the result as a pandas DataFrame.
    """
    # Query to select all rows from DishHistory
    dish_history_query = select(DishHistory.menu, DishHistory.menuDate, DishHistory.menuLine, DishHistory.studentPrice,DishHistory.guestPrice,DishHistory.icons_clean)

    # Query to select rows from Dish not in DishHistory
    dish_not_in_history_query = select(
        Dish.menu, Dish.menuDate, Dish.menuLine, Dish.studentPrice,Dish.guestPrice,FiltersClean.icons_clean
    ).join(
        FiltersClean, Dish.id == FiltersClean.menu_id
    ).where(
        not_(
            db_session.query(DishHistory)
            .filter(
                and_(
                    Dish.menu == DishHistory.menu,
                    Dish.menuDate == DishHistory.menuDate,
                    Dish.menuLine == DishHistory.menuLine                   
                )
            )
            .exists()
        )
    )

    # Combine both queries using UNION
    combined_query = union(dish_history_query, dish_not_in_history_query)

    # Execute the combined query and fetch all results
    result = db_session.execute(combined_query).fetchall()

    # Convert the result to a pandas DataFrame
    df = pd.DataFrame(result, columns=["menu", "menuDate", "menuLine", "studentPrice", "guestPrice","icons_clean"])
    df['menuDate'] = pd.to_datetime(df['menuDate'],format='%Y-%m-%d')

    # in the Dish table, the menuLines "Auswahlgericht" and "Auswahlgericht 2" can be combined
    df.loc[df['menuLine'] == 'Auswahlgericht vegan 2', 'menuLine'] = 'Auswahlgericht vegan'
    df.loc[df['menuLine'] == 'Auswahlgericht veget. 2', 'menuLine'] = 'Auswahlgericht veget.'
    df.loc[df['menuLine'] == 'Auswahlgericht 2', 'menuLine'] = 'Auswahlgericht'
    df.loc[df['menuLine'] == 'mensaVital vegan 2', 'menuLine'] = 'mensaVital vegan'

    # remove dishes with negative prices.
    df = df[(df['studentPrice'] >= 0) | (df['guestPrice'] >= 0)]

    # remove Pizza menuLine. Is this this was a mistake
    df = df[df['menuLine'] != "Pizza"]

    return df




def get_embedding_cluster(db_session):
    query = db_session.query(EmbeddingCluster).all()
    df = convert_dblist_to_df(query)
    df['centroid'] = df['centroid'].apply(
            lambda x: np.array(eval(x)) if isinstance(x, str) else np.array(x)
        )
    return df

def get_dish_vector(db_session, menu_id):
    query = db_session.query(Embedding.embedding).filter(Embedding.menu_id == menu_id).first()
    return np.array(eval(query[0]))

def get_cluster_similarity(db_session,user_name):
    
    # get user vector
    query = get_user_by_username(db_session,user_name)
    user_vector = np.array(eval(query.user_vector))

    # get centroid df
    centroid_df = get_embedding_cluster(db_session)

    # get centroids
    centroids = np.vstack(centroid_df['centroid'])

    # Compute cosine similarity
    similarity_scores = cosine_similarity([user_vector], centroids)[0]
    centroid_df['cosine_similarity'] = similarity_scores
    centroid_df.sort_values('cosine_similarity', ascending=False)

    # scale cosine similarity
    scaler = MinMaxScaler()
    centroid_df["min_max_scaler"] = scaler.fit_transform(centroid_df.cosine_similarity.values.reshape(-1,1))
    centroid_df["scaled"] = centroid_df["cosine_similarity"].apply(lambda x: (x - 0.5) / 0.5)


    return centroid_df


def get_week_recommended_dishes(db_session, week_dates, user_name, selected_lang):

    # get dishes for the week
    query = db_session.query(Dish).filter(
        Dish.menuDate.in_(week_dates),
        Dish.menu != "NA"
    )

    # Join additional tables
    query = (
        query
        .outerjoin(FiltersClean, Dish.id == FiltersClean.menu_id)
        .outerjoin(Recipe, Dish.id == Recipe.menu_id)
        .outerjoin(Description, Dish.id == Description.menu_id)
        .outerjoin(DishEng, Dish.id == DishEng.menu_id)
        .outerjoin(Course, Dish.id == Course.menu_id)
        .outerjoin(Embedding, Dish.id == Embedding.menu_id)
        .outerjoin(PriceClean, Dish.id == PriceClean.menu_id)
        .add_columns(
            Dish.id,Dish.menu,Dish.menuLine,Dish.studentPrice,Dish.guestPrice,Dish.allergens,Dish.additives,Dish.location,
            FiltersClean.icons_clean.label("icons_clean"),
            Recipe.recipe_de,
            Description.description_de,
            Embedding.embedding,
            Course.course,
            PriceClean.studentPrice_imputed,
            PriceClean.guestPrice_imputed,
            *( 
                [DishEng.menuLineEng, DishEng.menuEng, Description.description_en, Recipe.recipe_en, Course.course_eng]
                if selected_lang == "en" else []
            )
        )
    )
    # Convert to DataFrame
    df = pd.DataFrame(query.all())

    # get user vector
    user_vector = get_user_vector(user_name, db_session)

    # Compute cosine similarity if user vector exists
    if user_vector:
        df["cosine_similarity"] = df["embedding"].apply(lambda x: compute_cosine_similarity(x, user_vector))

    return df

def get_prevornext_weekday_dates(start_date: str, direction: str) -> list:
    """
    Get the week dates (Monday to Friday) for the previous or next week.

    Args:
    - start_date (str): The date of a Monday in "YYYY-MM-DD" format.
    - direction (str): "back" for the previous week, "next" for the next week.

    Returns:
    - list: List of week dates (Monday to Friday) as strings in "YYYY-MM-DD" format.
    """
    # Parse the input date
    current_monday = datetime.strptime(start_date, "%Y-%m-%d")
    
    # Determine the offset based on the direction
    if direction == "back":
        offset = -7  # Previous week
    else:
        offset = 7  # Next week
    
    # Calculate the Monday of the target week
    target_monday = current_monday + timedelta(days=offset)
    
    # Generate the week dates (Monday to Friday)
    week_dates = [(target_monday + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(5)]
    
    return week_dates

def get_weekday_dates():
    today = datetime.today()
    start_of_week = today - timedelta(days=today.weekday())  # Get Monday of the current week

    weekdays = [(start_of_week + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(5)]  # Monday to Friday
    return weekdays


def get_current_month_spending(session: Session, user_name , lang='en'):
    
    current_year = datetime.utcnow().year
    current_month = datetime.utcnow().month
    current_month_name = get_month_name(current_month, lang)

    result = session.query(
        func.sum(Dish.studentPrice).label('total_student_spending'),
        func.sum(Dish.guestPrice).label('total_guest_spending'),
        func.sum(Dish.pupilPrice).label('total_pupil_spending')
    ).select_from(Rating).join(
        Dish, Rating.menu_id == Dish.id
    ).filter(
        Rating.user_name == user_name,
        Rating.on_rating_page == False,
        extract('year', Rating.timestamp) == current_year,
        extract('month', Rating.timestamp) == current_month
    ).one_or_none()
        
    df = pd.DataFrame([{
        'year': current_year,
        'month': current_month,
        'month_name': current_month_name,
        'student': result.total_student_spending if result and result.total_student_spending else 0.0,
        'guest': result.total_guest_spending if result and result.total_guest_spending else 0.0,
        'pupil': result.total_pupil_spending if result and result.total_pupil_spending else 0.0
    }])  
        
    return df



def get_past_6_month_spending(session: Session, user_name, lang='en'):
    current_year = datetime.utcnow().year
    current_month = datetime.utcnow().month

    # List to store data for the past 6 months
    month_data = []

    for i in [0, 1, 2, 3, 4, 5]:
        # Calculate the month and year for each of the last 6 months
        month_offset = (current_month - i) if (current_month - i) > 0 else (12 + (current_month - i))
        year_offset = current_year if current_month - i > 0 else current_year - 1
        month_name = get_month_name(month_offset, lang)

        result = session.query(
            func.sum(Dish.studentPrice).label('total_student_spending'),
            func.sum(Dish.guestPrice).label('total_guest_spending'),
            func.sum(Dish.pupilPrice).label('total_pupil_spending')
        ).select_from(Rating).join(
            Dish, Rating.menu_id == Dish.id
        ).filter(
            Rating.user_name == user_name,
            Rating.on_rating_page == False,
            extract('year', Rating.timestamp) == year_offset,
            extract('month', Rating.timestamp) == month_offset  # Adjust month for 1-12 range
        ).one_or_none()

        # Append the data for the current month
        month_data.append({
            'year': year_offset,
            'month': month_offset,
            'month_name': month_name,
            'student': result.total_student_spending if result and result.total_student_spending else 0.0,
            'guest': result.total_guest_spending if result and result.total_guest_spending else 0.0,
            'pupil': result.total_pupil_spending if result and result.total_pupil_spending else 0.0
        })

    #Create df
    df = pd.DataFrame(month_data)

    return df
    
