from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Date
import pandas as pd
import sys
from datetime import datetime

Base = declarative_base()

# Define the Dish model with updated structure
class Dish(Base):
    __tablename__ = 'dishes'

    id = Column(Integer, primary_key=True)
    menuDate = Column(Date, nullable=True)
    menuLine = Column(String, nullable=True)
    menu = Column(String, nullable=True)
    studentPrice = Column(Float, nullable=True)
    location = Column(String, nullable=True)
    guestPrice = Column(Float, nullable=True)
    pupilPrice = Column(Float, nullable=True)
    meats = Column(String, nullable=True)
    icons = Column(String, nullable=True)
    allergens = Column(String, nullable=True)
    additives = Column(String, nullable=True)

class Rating(Base):
    __tablename__ = 'rating'
    id = Column(Integer, primary_key=True)
    menu_id = Column(Integer, nullable=False)
    rating = Column(Integer, nullable=False)
    timestamp = Column(DateTime,default=datetime.now, nullable=False)

def setup_database_connection(user, password, host, port):
    try:
        connection_string = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/postgres"
        engine = create_engine(connection_string)
        engine.connect()
        print("Successfully connected to database")
        return engine, sessionmaker(bind=engine)
    except Exception as e:
        print(f"Error connecting to database: {str(e)}")
        sys.exit(1)

def write_to_db(filtered_df: pd.DataFrame, engine, Session):
    Dish.metadata.create_all(engine)

    with Session() as session:
        for _, row in filtered_df.iterrows():
            try:
                # Check if menuDat + menuLine + menu combination already exists in the database then skip
                # e.g. 2024-12-16 + Frisches Obst + Dessert SB -> skipped if exists
                existing_dish = session.query(Dish).filter(
                    Dish.menuDate == row.get('menuDate'),
                    Dish.menuLine == row.get('menuLine'),
                    Dish.menu == row.get('menu')
                ).first()
    
                if not existing_dish:
                    student_price = row.get('studentPrice', 0)
                    student_price = -1 if student_price == '-' else float(student_price.replace(',', '.'))
                    
                    guest_price = row.get('guestPrice', 0)
                    guest_price = -1 if guest_price == '-' else float(guest_price.replace(',', '.'))
                    
                    pupil_price = row.get('pupilPrice', 0)
                    pupil_price = -1 if pupil_price == '-' else float(pupil_price.replace(',', '.'))
                    
                    dish = Dish(
                        menuDate=row.get('menuDate'),
                        menuLine=row.get('menuLine'),
                        menu=row.get('menu'),
                        studentPrice=student_price,
                        location=row.get('location'),
                        guestPrice=guest_price,
                        pupilPrice=pupil_price,
                        meats=row.get('meats'),
                        icons=row.get('icons'),
                        allergens=row.get('allergens'),
                        additives=row.get('additives'),
                    )
                    session.add(dish)
            except ValueError as e:
                print(f"Error converting values for row: {row}")
                print(f"Error message: {str(e)}")
                continue
        session.commit()

# create a new table called rating. it should contain two columns: id and rating
def write_to_rating(id: int, rating: int, engine, Session):
    Rating.metadata.create_all(engine)

    with Session() as session:
        rating = Rating(menu_id=id, rating=rating)
        session.add(rating)
        session.commit()