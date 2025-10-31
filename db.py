import os
from sqlalchemy import create_engine

def get_engine():
    url = os.getenv("DQ_DB_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/synthetic_bank")
    return create_engine(url)
