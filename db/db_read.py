from sqlalchemy.orm import Session
from .db_write import Dish, setup_database_connection
from typing import List


def get_user_by_username(session: Session, username: str):
    return session.query(User).filter_by(username=username).first()

def get_dishes_by_date_location(session: Session, date, location) -> List[Dish]:
    return session.query(Dish).filter_by(menuDate=date, location=location).all()

def get_all_dishes(session: Session) -> List[Dish]:
    return session.query(Dish).all()

def get_image_path(dish_id: int, session: Session) -> str:
    dish = session.query(Dish).filter_by(id=dish_id).first()
    return dish.image_path if dish else None

from datetime import datetime, timedelta

def get_next_five_days_data(session: Session) -> dict:
    today = datetime.now().date()
    date_range = [today + timedelta(days=x) for x in range(5)]
    
    results = {}
    for date in date_range:
        dishes = session.query(Dish).filter_by(menuDate=date).all()
        locations = list(set(dish.location for dish in dishes))
        results[date.strftime('%A, %Y-%m-%d')] = locations
    
    return results