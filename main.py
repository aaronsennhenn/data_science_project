from archive.scraper_daniel import *
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Date
from secret import USER, PASSWORD, HOST, PORT
from sqlalchemy import create_engine
import pandas as pd
from sqlalchemy.orm import sessionmaker


# Connection string
connection_string = f"postgresql+psycopg2://{USER}:{PASSWORD}@{HOST}:{PORT}/postgres"
engine = create_engine(connection_string)

# Create session factory
Session = sessionmaker(bind=engine)

# Base class for ORM models
db = declarative_base()

# Define your Dish model
class Dish(db):
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


def safe_menus_to_db(url_dict):
    
    result_df = pd.DataFrame(columns=["id","menuLine","studentPrice","guestPrice","pupilPrice","menuDate","menu","meats","icons","allergens","additives","location","filtersInclude"])
    
    for _,value in enumerate(url_dict):
        temp = run_scraper(value)
        result_df = pd.concat([result_df,temp])

    # get dates of next 7 days without weekends
    available_dates = get_available_dates()
    filtered_df = result_df[result_df["menuDate"].isin(available_dates)]
    filtered_df["menu"] = filtered_df['menu'].apply(lambda row: remove_brackets(row))
    filtered_df["guestPrice"] = filtered_df["guestPrice"].str.replace(',','.')
    filtered_df["studentPrice"] = filtered_df["studentPrice"].str.replace(',','.')

  

    # Dynamically create tables if not initialized
    Dish.metadata.create_all(engine)

    #print(filtered_df.filtersInclude)
    # Extract the dates that already exist in the database
    with Session() as session:  # Use 'with' to handle session lifecycle
        existing_dates = [result[0].strftime('%Y-%m-%d') for result in session.query(Dish.menuDate).distinct().all()]

        # Filter out dishes for dates already in the database
        new_entries_df = filtered_df[~filtered_df["menuDate"].isin(existing_dates)]

        # translate to english
     #   new_entries_df["menu_eng"] = new_entries_df['menu'].apply(lambda x:translate_text(x))


        ####

        # TO BE DONE: STABLE DIFFUSION FUNCTION - ADD IMAGE NAME COLUMN TO DATAFRAME AND GENERATE IMAGE, STORE IMAGE TO FOLDER
    
        ####

        # Store new dishes in the database
        for _, row in new_entries_df.iterrows():
            new_dish = Dish(menuDate=row['menuDate'], location=row['location'], menuGer=row['menu'],menuLine=row['menuLine'] ,guestPrice=row['guestPrice'], studentPrice=row['studentPrice'], meats=row['meats'], icons=row['icons'],filters=row['filtersInclude'],allergens=row['allergens'],additives=row['additives'])
            session.add(new_dish)



        # Commit the transaction
        session.commit()

    session.close()



if __name__ == "__main__":
    safe_menus_to_db(url_dict)