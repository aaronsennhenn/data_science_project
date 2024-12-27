"""
This file gets the queries new entries from the dishe stable and runs GPT prompts on it.
The results from the prompts are then saved to the respective database tables.
It is supposed to be run as a cronjob, sometime after the scraping cronjob has finished.
"""

from db.db_read import get_all_dishes, convert_dblist_to_df
from db.db_write import setup_database_connection, write_to_embedding, Embedding
from scraper.gpt_prompts import embedding_extraction, initialize_openai_client
from secret import USER, PASSWORD, HOST, PORT, OPENAI_KEY
import pandas as pd


client = initialize_openai_client(OPENAI_KEY) #Setup Open AI Client
engine, Session = setup_database_connection(USER, PASSWORD, HOST, PORT) #Setup Database connection


def main():

    with Session() as db_session:
    
        #Read
        dishes_db_list = get_all_dishes(db_session) #Query database    
        dishes_df = convert_dblist_to_df(dishes_db_list) #Convert to df

        
        #Prompt and write to db for embeddings
        dishes_df = embedding_extraction(dishes_df, 'menu')     
        write_to_embedding(dishes_df, engine, db_session)
        
        #Promt and write for .....
        


    if __name__ == "__main__":
        main()
