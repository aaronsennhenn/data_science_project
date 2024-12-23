from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Date
import pandas as pd
import sys
from datetime import datetime

Base = declarative_base()

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

class Directory(Base):
    __tablename__ = 'directory'
    id = Column(Integer, primary_key=True, autoincrement=True)
    additives = Column(String, nullable=True)
    additives_written = Column(String, nullable=True)
    allergens = Column(String, nullable=True)
    allergens_written = Column(String, nullable=True)


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

# create a new table called directory, that includes the abbreviations saved in additives and allergens and their corresponding written out form
def write_to_directory(engine, Session):
    Directory.metadata.create_all(engine)
    
    additives_map = {
        '9': 'Süßungsmittel',
        '1': 'Farbstoff',
        '2': 'Konservierungsstoff',
        '3': 'Nitritpökelsalz',
        '4': 'Antioxidationsmittel',
        '5': 'Geschmacksverstärker',
        '11': 'Phosphat'
    }
    
    allergens_map = {
        'Ei': 'Eier',
        'Se': 'Sellerie',
        'ML': 'Milch / Laktose',
        'Sa': 'Sesam',
        'Gl-a': 'Weizen',
        'So': 'Soja',
        'Nu-a': 'Mandeln'
    }
    
    with Session() as session:
        # Get unique additives and allergens from dishes table
        unique_additives = session.query(Dish.additives).distinct().all()
        unique_allergens = session.query(Dish.allergens).distinct().all()
        
        # Process additives
        for additive in unique_additives:
            if additive[0]:
                codes = [code.strip() for code in additive[0].split(',')]
                for code in codes:
                    existing = session.query(Directory).filter_by(additives=code).first()
                    if not existing:
                        directory_entry = Directory(
                            additives=code,
                            additives_written=additives_map.get(code, None)
                        )
                        session.add(directory_entry)
        
        # Process allergens
        for allergen in unique_allergens:
            if allergen[0]:
                codes = [code.strip() for code in allergen[0].split(',')]
                for code in codes:
                    existing = session.query(Directory).filter_by(allergens=code).first()
                    if not existing:
                        directory_entry = Directory(
                            allergens=code,
                            allergens_written=allergens_map.get(code, None)
                        )
                        session.add(directory_entry)
                
        session.commit()
