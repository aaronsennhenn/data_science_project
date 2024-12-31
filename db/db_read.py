from sqlalchemy.orm import Session
from .db_write import Dish, DishEng,  Directory, setup_database_connection, User, Rating, Course, Description, Recipe, Embedding, FiltersClean
from typing import List
from sqlalchemy import func
import datetime
import pandas as pd

def convert_dblist_to_df(db_list):
    dict_list = [vars(obj) for obj in db_list]
    for dictionary in dict_list:
        dictionary.pop('_sa_instance_state', None)
    df = pd.DataFrame(dict_list)        
    return df
        
def get_user_by_username(session: Session, username: str):
    return session.query(User).filter_by(username=username).first()

#def get_dishes_by_date_location(session: Session, date, location) -> List[Dish]:
#    return session.query(Dish).filter_by(menuDate=date, location=location).all()

def get_dishes_by_date_location(session: Session, date, location) -> List[Dish]:
   return session.query(Dish,Embedding.embedding).outerjoin(Embedding,Dish.id == Embedding.menu_id).filter(Dish.menuDate == date,Dish.location == location).all()    

def get_all_dishes(session: Session) -> List[Dish]:
    return session.query(Dish).all()

def get_dishes_by_date(session: Session, date) -> List[Dish]:
    return session.query(Dish,Embedding.embedding).outerjoin(Embedding,Dish.id == Embedding.menu_id).filter(Dish.menuDate == date).all()

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

    
def load_dishes_table_for_filter_cleaning(Session):
    """
    Loads dishes from the Dish table that are not contained in the FiltersClean table (based on id)
    and returns them as a DataFrame.

    Args:
        Session: SQLAlchemy session factory.

    Returns:
        pd.DataFrame: A DataFrame of dishes not present in FiltersClean.
    """
    with Session() as session:
        # Query for dishes not in FiltersClean
        dishes = session.query(
            Dish.id,
            Dish.menuLine,
            Dish.menu,
            Dish.icons
        ).filter(
            ~session.query(FiltersClean).filter(FiltersClean.menu_id == Dish.id).exists()
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
    date_range = [datetime(2024, 12, 17), datetime(2024, 12, 18), datetime(2024, 12, 19), datetime(2024, 12, 20)]
    
    results = {}
    for date in date_range:
        dishes = session.query(Dish).filter_by(menuDate=date).all()
        locations = list(set(dish.location for dish in dishes))
        results[date.strftime('%A, %Y-%m-%d')] = locations
    
    return results

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
# Display all prices (Dish.pupilPrice Dish.studentPrice and Dish.guestPrice) 
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

#Get top three dishes of the week - on y-axis the rating average and on x-axis the dish name (menu)
#table "rating" use menu_id and rating columns and then merge the table "dishes" to find with the menu_id the corresponding dish name saved in column menu
def get_top_three_dishes(session: Session):
    today = datetime.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    # Query to get top three dishes
    top_dishes = session.query(
        Dish.menu,
        func.avg(Rating.rating).label('avg_rating')
    ).join(Rating, Dish.id == Rating.menu_id
    ).filter(
        Dish.menuDate.between(start_of_week, end_of_week)
    ).group_by(
        Dish.id
    ).order_by(
        func.avg(Rating.rating).desc()
    ).limit(3).all()
    #Format result
    result = [
        {
            'dish_name': dish.menu,
            'avg_rating': round(dish.avg_rating, 2)
        } for dish in top_dishes
    ]
    return result

# #Testing
# def get_top_three_dishes(session: Session):
#     # Query to get top three dishes based on all ratings
#     top_dishes = session.query(
#         Dish.menu,
#         func.avg(Rating.rating).label('avg_rating'),
#         func.count(Rating.id).label('rating_count')
#     ).join(Rating, Dish.id == Rating.menu_id
#     ).group_by(
#         Dish.id
#     ).order_by(
#         func.avg(Rating.rating).desc()
#     ).limit(3).all()

#     # Format result
#     result = [
#         {
#             'dish_name': dish.menu,
#             'avg_rating': round(dish.avg_rating, 2),
#             'rating_count': dish.rating_count
#         } for dish in top_dishes
#     ]
    
#     return result


#Get top three mensas of the week (ranked best first) - on y-axis the rating average and on x-axis the location (mensa)
def get_top_three_mensas(session: Session):
    # Get the start and end dates for the current week
    today = datetime.now().date()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    # Query to get top three mensas
    top_mensas = session.query(
        Dish.location,
        func.avg(Rating.rating).label('avg_rating')
    ).join(Rating, Dish.id == Rating.menu_id
    ).filter(
        Dish.menuDate.between(start_of_week, end_of_week)
    ).group_by(
        Dish.location
    ).order_by(
        func.avg(Rating.rating).desc()
    ).limit(3).all()
    #Format result
    result = [
        {
            'location': mensa.location,
            'avg_rating': round(mensa.avg_rating, 2)
        } for mensa in top_mensas
    ]
    return result

# Account Analysis
# Get total number of ratings a user submitted
def get_total_ratings_by_user(session: Session, username: str) -> int:
    return session.query(func.count(Rating.id)).filter(Rating.user_name == username).scalar()

# Get date of first rating of user
def get_first_rating_date_of_user(session: Session, username: str) -> str:
    first_rating = session.query(func.min(Rating.timestamp)).filter(Rating.user_name == username).scalar()
    if first_rating:
        return first_rating.strftime('%Y-%m-%d')
    return None

# Get favorite dishes (top 3) of user
def get_favorite_dishes_of_user(session: Session, username: str, lang: str = 'en', limit: int = 3):
    favorite_dishes = session.query(
        Dish.id,
        Dish.menu,
        DishEng.menuEng,
        Rating.rating
    ).join(Rating, Dish.id == Rating.menu_id
    ).outerjoin(DishEng, Dish.id == DishEng.menu_id
    ).filter(Rating.user_name == username
    ).order_by(Rating.rating.desc()
    ).limit(limit).all()

    return [(dish.menuEng if lang == 'en' else dish.menu, dish.rating) for dish in favorite_dishes]

# Get favorite mensas (top 3) of user
def get_favorite_mensas_of_user(session: Session, username: str, lang: str = 'en', limit: int = 3):
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

    return [(mensa.locationEng if lang == 'en' else mensa.location, round(mensa.avg_rating, 2)) for mensa in favorite_mensas]