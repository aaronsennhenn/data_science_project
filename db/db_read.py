from sqlalchemy.orm import Session
from .db_write import Dish, Directory, setup_database_connection, User, Rating
from typing import List
from sqlalchemy import func
import datetime 

def get_user_by_username(session: Session, username: str):
    return session.query(User).filter_by(username=username).first()

def get_dishes_by_date_location(session: Session, date, location) -> List[Dish]:
    return session.query(Dish).filter_by(menuDate=date, location=location).all()

def get_all_dishes(session: Session) -> List[Dish]:
    return session.query(Dish).all()

def get_image_path(dish_id: int, session: Session) -> str:
    dish = session.query(Dish).filter_by(id=dish_id).first()
    return dish.image_path if dish else None

def get_meat_options(session: Session) -> List[str]:
    return session.query(Dish.meats).distinct().all()

from datetime import datetime, timedelta

def get_next_five_days_data(session: Session) -> dict:
    today = datetime.now().date()
    date_range = [today + timedelta(days=x) for x in range(5)]

    # MANUALLY FIX DATES OVER CHRISTMAS PERIOD BECAUSE MENSA IS CLOSED. MUST BE REMOVED AFTER CHRISTMAS
    date_range = [datetime(2024, 12, 15), datetime(2041, 12, 16), datetime(2024, 12, 17), datetime(2024, 12, 18), datetime(2024, 12, 19), datetime(2024, 12, 20)]
    
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

# Average Menu Prices per Each Mensa (Dish.menu) over all prices (Dish.pupilPrice Dish.studentPrice and Dish.guestPrice) but grouped by each menu line (Dish.menuLine)
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

# Lowest Menu Prices per Each Mensa (Dish.menu) over all prices (Dish.pupilPrice Dish.studentPrice and Dish.guestPrice) but grouped by each menu line (Dish.menuLine)
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
    """Get written forms of additives and allergens from Directory"""
    additives_dict = {}
    allergens_dict = {}
    
    directory_entries = session.query(Directory).all()
    
    for entry in directory_entries:
        if entry.additives:
            additives_dict[entry.additives] = entry.additives_written
        if entry.allergens:
            allergens_dict[entry.allergens] = entry.allergens_written
            
    return additives_dict, allergens_dict

def get_user_name(db_session, username):
    return db_session.query(User).filter_by(username=username).first()
    