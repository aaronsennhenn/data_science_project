from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Date
import pandas as pd
import sys

Base = declarative_base()

# Define the Dish model
class Dish(Base):
    __tablename__ = 'dishes'

    id = Column(Integer, primary_key=True)
    menuDate = Column(Date, nullable=True)
    location = Column(String, nullable=True)
    menuGer = Column(String, nullable=True)
    menuEng = Column(String, nullable=True)
    guestPrice = Column(String, nullable=True)
    studentPrice = Column(String, nullable=True)
    meats = Column(String, nullable=True)
    icons = Column(String, nullable=True)
    filters = Column(String, nullable=True)
    allergens = Column(String, nullable=True)
    additives = Column(String, nullable=True)
    menuLine = Column(String, nullable=True)
    descriptionGer = Column(String, nullable=True)
    descriptionEn = Column(String, nullable=True)
    taste = Column(String, nullable=True)
    ingredients = Column(String, nullable=True)
    tokens = Column(Integer, nullable=True)
    image_path = Column(String, nullable=True)

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
            # Check if image_path already exists. dont write if it does
            existing_dish = session.query(Dish).filter(Dish.image_path == row.get('image_path')).first()
            
            if not existing_dish:
                dish = Dish(
                    menuDate=row.get('menuDate'),
                    location=row.get('location'),
                    menuGer=row.get('menuGer'),
                    menuEng=row.get('menuEng'),
                    guestPrice=row.get('guestPrice'),
                    studentPrice=row.get('studentPrice'),
                    meats=row.get('meats'),
                    icons=row.get('icons'),
                    filters=row.get('filters'),
                    allergens=row.get('allergens'),
                    additives=row.get('additives'),
                    menuLine=row.get('menuLine'),
                    descriptionGer=row.get('descriptionGer'),
                    descriptionEn=row.get('descriptionEn'),
                    taste=row.get('taste'),
                    ingredients=row.get('ingredients'),
                    tokens=row.get('tokens'),
                    image_path=row.get('image_path'),
                )
                session.add(dish)
        session.commit()
