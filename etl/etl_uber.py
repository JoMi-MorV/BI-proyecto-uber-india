import os
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()
url = (f"postgresql+psycopg2://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}"
       f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}")
engine = create_engine(url)

with engine.connect() as conn:
    print(conn.execute(text("SELECT version()")).scalar())

df = pd.read_csv("data/raw/uber_india_2024.csv")
print(df.shape)  # esperado: (150000, 21)