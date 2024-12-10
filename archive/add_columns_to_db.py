from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from secret import USER, PASSWORD, HOST, PORT

# Connection string
connection_string = f"postgresql+psycopg2://{USER}:{PASSWORD}@{HOST}:{PORT}/postgres"
engine = create_engine(connection_string)

# Create session factory
Session = sessionmaker(bind=engine)

# Function to add new columns to the dishes table
def add_columns_to_dishes():
    try:
        # Start a new session
        with Session() as session:
            # Execute the SQL query to add the new columns using the 'text' function
            ###### DAS HIER ANPASSEN ###########
            session.execute(text('''
                ALTER TABLE dishes ADD COLUMN "descriptionGer" TEXT;
            '''))
            
            # Commit the transaction
            session.commit()
            print("Columns added successfully.")
    
    except Exception as e:
        print(f"An error occurred: {e}")
        session.rollback()  # Rollback in case of error

# Call the function to add columns
if __name__ == "__main__":
    add_columns_to_dishes()