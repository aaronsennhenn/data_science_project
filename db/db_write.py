from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Date
import pandas as pd
import sys
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from secret import *
from db.utils import translate_text_first_word_capitalized, translate_text_all_capitalized
import numpy as np

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

class FiltersClean(Base):
    __tablename__ = "filters_clean"
    id = Column(Integer, primary_key=True)
    menu_id = Column(Integer, nullable=False)
    icons_clean = Column(String, nullable=True)


class DishEng(Base):
    __tablename__ = 'dishes_eng'
    id = Column(Integer, primary_key=True)
    menu_id = Column(Integer, nullable=False)
    menuDate = Column(Date, nullable=True)
    menuLineEng = Column(String, nullable=True)
    menuEng = Column(String, nullable=True)
    locationEng = Column(String, nullable=True)

class Rating(Base):
    __tablename__ = 'rating'
    id = Column(Integer, primary_key=True)
    user_name = Column(String, nullable=True)
    menu_id = Column(Integer, nullable=False)
    rating = Column(Integer, nullable=False)
    timestamp = Column(DateTime,default=datetime.now, nullable=False)

class Directory(Base):
    __tablename__ = 'directory'
    id = Column(Integer, primary_key=True, autoincrement=True)
    additives = Column(String, nullable=True)
    additives_written = Column(String, nullable=True)
    additives_written_eng = Column(String, nullable=True)
    allergens = Column(String, nullable=True)
    allergens_written = Column(String, nullable=True)
    allergens_written_eng = Column(String, nullable=True)
    meats = Column(String, nullable=True)
    meats_written = Column(String, nullable=True)
    meats_written_eng = Column(String, nullable=True)
    
class Ingredient(Base):
    __tablename__ = 'ingredients'
    id = Column(Integer, primary_key=True)
    menu_id = Column(Integer, nullable=False)
    ingredients_de = Column(String, nullable=True)
    ingredients_en = Column(String, nullable=True)

class Embedding(Base):
    __tablename__ = 'embeddings'
    id = Column(Integer, primary_key=True)
    menu_id = Column(Integer, nullable=False)
    embedding = Column(String, nullable=True)
    
class Description(Base):
    __tablename__ = 'descriptions'
    id = Column(Integer, primary_key=True)
    menu_id = Column(Integer, nullable=False)
    description_de = Column(String, nullable=True)
    description_en = Column(String, nullable=True)
    
class Recipe(Base):
    __tablename__ = 'recipes'
    id = Column(Integer, primary_key=True)
    menu_id = Column(Integer, nullable=False)
    recipe_de = Column(String, nullable=True)
    recipe_en = Column(String, nullable=True)
    
class Taste(Base):
    __tablename__ = 'tastes'
    id = Column(Integer, primary_key=True)
    menu_id = Column(Integer, nullable=False)
    taste_de = Column(String, nullable=True)
    taste_en = Column(String, nullable=True)

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=True)
    user_vector = Column(String, nullable=True)

    def add_vector(self, vector):
        self.user_vector = vector

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Course(Base):
    __tablename__ = 'course'

    id = Column(Integer, primary_key=True, autoincrement=True)  # Add this line
    menu_id = Column(Integer, nullable=True)
    course = Column(String, nullable=True)
    course_eng = Column(String, nullable=True)

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

    with Session() as db_session:
        for _, row in filtered_df.iterrows():
            try:
                # Check if menuDat + menuLine + menu combination already exists in the database then skip
                # e.g. 2024-12-16 + Frisches Obst + Dessert SB -> skipped if exists
                existing_dish = db_session.query(Dish).filter(
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
                    db_session.add(dish)
            except ValueError as e:
                print(f"Error converting values for row: {row}")
                print(f"Error message: {str(e)}")
                continue

        
        db_session.commit()

# Save translations of dishes in a separate table (api calls avoided)
def write_to_dishes_eng(engine, Session):
    DishEng.metadata.create_all(engine)
    
    with Session() as db_session:
        dishes = db_session.query(Dish).all()
        
        for dish in dishes:
            # Check if translation already exists
            existing = db_session.query(DishEng).filter(
                DishEng.menu_id == dish.id,
            ).first()
            
            if not existing:
                dish_eng = DishEng(
                    menu_id=dish.id,  # Add this line to include the menu_id
                    menuDate=dish.menuDate,
                    menuLineEng=translate_text_all_capitalized(dish.menuLine),
                    menuEng=translate_text_first_word_capitalized(dish.menu),
                    locationEng=translate_text_all_capitalized(dish.location)
                )
                db_session.add(dish_eng)
        
        db_session.commit()
    

# This table contains the user ratings, the menu_id of the rated meal, a timestamp, and the user_id if he is logged in
def write_to_rating(menu_id: int, rating: int, user_name: int, engine, Session):
    Rating.metadata.create_all(engine) 

    with Session() as db_session:
        rating = Rating(menu_id=menu_id, rating=rating, user_name=user_name)
        db_session.add(rating)
        db_session.commit()

def write_to_filters_clean(icons_df: pd.DataFrame, engine, session):
    FiltersClean.metadata.create_all(engine) 

    for _, row in icons_df.iterrows():
        try:
            icons = FiltersClean(
                menu_id=int(row.get('id')),
                icons_clean=str(row.get('icons_clean')),
            )
            session.add(icons)
            session.commit()
        except ValueError as e:
            print(f"Error message: {str(e)}")
            continue



def write_to_user(username: str, password: str, engine, Session):
    User.metadata.create_all(engine)

    with Session() as db_session:
        user = User(username=username)
        user.set_password(password)
        user.add_vector(vector = None)
        db_session.add(user)
        db_session.commit()


def write_to_ingredient(dishes_df: pd.DataFrame, engine, session):
    Ingredient.metadata.create_all(engine)

    for _, row in dishes_df.iterrows():
        try:
            ingredients = Ingredient(
                menu_id=row.get('id'),
                ingredients_de=row.get('ingredients_de'),
                ingredients_en=row.get('ingredients_en')
            )
            session.add(ingredients)
        except ValueError as e:
            print(f"Error converting values for row: {row.to_dict()}")
            print(f"Error message: {str(e)}")
            continue


def write_to_description(dishes_df: pd.DataFrame, engine, session):
    Description.metadata.create_all(engine)

    for _, row in dishes_df.iterrows():
        try:
            description = Description(
                menu_id=row.get('id'),
                description_de=row.get('description_de'),
                description_en=row.get('description_en')
            )
            session.add(description)
            session.commit()
        except ValueError as e:
            print(f"Error converting values for row: {row.to_dict()}")
            print(f"Error message: {str(e)}")
            continue


def write_to_embedding(dishes_df: pd.DataFrame, engine, session):
    Embedding.metadata.create_all(engine)

    for _, row in dishes_df.iterrows():
        try:
            embedding = Embedding(
                menu_id=row.get('id'),
                embedding=row.get('gpt_embedding'),
            )
            session.add(embedding)
            session.commit()
            
        except ValueError as e:
            print(f"Error converting values for row: {row.to_dict()}")
            print(f"Error message: {str(e)}")
            continue


def write_to_recipe(dishes_df: pd.DataFrame, engine, session):
    Recipe.metadata.create_all(engine)

    for _, row in dishes_df.iterrows():
        try:
            recipe = Recipe(
                menu_id=row.get('id'),
                recipe_de=row.get('recipe_de'),
                recipe_en=row.get('recipe_en')
            )
            session.add(recipe)
        except ValueError as e:
            print(f"Error converting values for row: {row.to_dict()}")
            print(f"Error message: {str(e)}")
            continue


def write_to_taste(dishes_df: pd.DataFrame, engine, session):
    Taste.metadata.create_all(engine)

    for _, row in dishes_df.iterrows():
        try:
            taste = Taste(
                menu_id=row.get('id'),
                taste_de=row.get('taste_de'),
                taste_en=row.get('taste_en')
            )
            session.add(taste)
        except ValueError as e:
            print(f"Error converting values for row: {row.to_dict()}")
            print(f"Error message: {str(e)}")
            continue

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

    meats_map = {
        'R': 'Rind',
        'S': 'Schwein',
        'G': 'Geflügel',
        'F': 'Fisch',
        'W': 'Wild',
        'L': 'Lamm',
        'K': 'Kalb',
        'V': 'Vegetarisch',
        'vegan': 'Vegan', 
        'top': 'Empfehlung',
        'vital': 'Vital'
    }
    
    with Session() as db_session:
        unique_additives = db_session.query(Dish.additives).distinct().all()
        unique_allergens = db_session.query(Dish.allergens).distinct().all()
        unique_meats = db_session.query(Dish.meats).distinct().all()

        # Process additives
        for additive in unique_additives:
            if additive[0]:
                codes = [code.strip() for code in additive[0].split(',')]
                for code in codes:
                    existing = db_session.query(Directory).filter_by(additives=code).first()
                    if not existing:
                        german_text = additives_map.get(code, None)
                        english_text = translate_text_first_word_capitalized(german_text) if german_text else None
                        directory_entry = Directory(
                            additives=code,
                            additives_written=german_text,
                            additives_written_eng=english_text
                        )
                        db_session.add(directory_entry)
        
        # Process allergens
        for allergen in unique_allergens:
            if allergen[0]:
                codes = [code.strip() for code in allergen[0].split(',')]
                for code in codes:
                    existing = db_session.query(Directory).filter_by(allergens=code).first()
                    if not existing:
                        german_text = allergens_map.get(code, None)
                        english_text = translate_text_first_word_capitalized(german_text) if german_text else None
                        directory_entry = Directory(
                            allergens=code,
                            allergens_written=german_text,
                            allergens_written_eng=english_text
                        )
                        db_session.add(directory_entry)

        # Process meats
        for meat in unique_meats:
            if meat[0]:
                codes = [code.strip() for code in meat[0].split(',')]
                for code in codes:
                    existing = db_session.query(Directory).filter_by(meats=code).first()
                    if not existing:
                        german_text = meats_map.get(code, None)
                        english_text = translate_text_first_word_capitalized(german_text) if german_text else None
                        directory_entry = Directory(
                            meats=code,
                            meats_written=german_text,
                            meats_written_eng=english_text
                        )
                        db_session.add(directory_entry)
                
        db_session.commit()


def write_to_course(engine, db_session):
    Course.metadata.create_all(engine)
    
    dishes = db_session.query(Dish).all()
    
    for dish in dishes:
        existing = db_session.query(Course).filter(Course.menu_id == dish.id).first()
        
        if not existing:
            main_dishes = ['Angebot des Tages', 'Tagesmenü', 'Tagesmenü vegan', 'Tagesmenü vegetarisch','Angebot d. Tages veget.','mensaVital vegan',
                            'Auswahlgericht', 'Auswahlgericht vegan 2', 'Auswahlgericht 2',
                            'Auswahlgericht veget.', 'Auswahlgericht vegan', 'mensaVital vegetarisch']
            
            side_dishes = ['Salat-/ Gemüsebuffet 100g', 'Beilagen vorport.', 'Beilagen SB']
            
            desserts = ['Dessert SB', 'Dessert vorport.']
            
            course = None
            course_eng = None
            
            if dish.menuLine in main_dishes:
                course = "Hauptspeise"
                course_eng = "Main Dish"
            elif dish.menuLine in side_dishes:
                course = "Beilage"
                course_eng = "Side Dish"
            elif dish.menuLine in desserts:
                course = "Nachspeise"
                course_eng = "Dessert"
            
            if course and course_eng:
                new_course = Course(
                    menu_id=dish.id,
                    course=course,
                    course_eng=course_eng
                )
                db_session.add(new_course)
    
    db_session.commit()


def update_user_vector(username, engine, Session):
    """
    Recomputes the user vector for a specific user based on their ratings and embeddings,
    and updates the user vector in the database.

    Args:
        username (str): The username of the user whose vector needs to be updated.
    """
    User.metadata.create_all(engine) 
    Embedding.metadata.create_all(engine)

    with Session() as db_session:
        # Join the ratings and embeddings tables, filtering by the provided username
        query = db_session.query(
            Rating,
            Embedding.embedding
        ).outerjoin(
            Embedding,
            Rating.menu_id == Embedding.menu_id
        ).filter(
            Rating.user_name == username  # Filter by the specific username
        )

        # Execute the query and fetch all results
        results = query.all()

        # Convert results to a DataFrame
        data = [
            {
                **rating.__dict__,
                "embedding": embedding
            }
            for rating, embedding in results
        ]

        # Remove SQLAlchemy state information
        for item in data:
            item.pop('_sa_instance_state', None)

        # Create DataFrame
        rating_with_embedding = pd.DataFrame(data)

        # Convert string embeddings to NumPy arrays
        rating_with_embedding['embedding'] = rating_with_embedding['embedding'].apply(
            lambda x: np.array(eval(x)) if isinstance(x, str) else np.array(x)
        )

        # Extract embeddings and ratings
        embeddings = np.stack(rating_with_embedding['embedding'].values)  # Convert to 2D array
        ratings = rating_with_embedding['rating'].values  # Extract ratings (1-5 scale)

        # Compute weighted embeddings
        weighted_embeddings = embeddings * ratings[:, np.newaxis]

        # Compute the weighted average user vector
        user_vector = np.sum(weighted_embeddings, axis=0) / np.sum(ratings)

        # Query the user in the database
        user = db_session.query(User).filter_by(username=username).first()

        # Update the user vector if the user exists
        if user:
            user.add_vector(str(user_vector.tolist()))  # Update user vector
            db_session.add(user)

        # Commit the changes
        db_session.commit()