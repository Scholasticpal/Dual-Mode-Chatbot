import os
from dotenv import load_dotenv
from supabase import create_client, Client
from langchain_community.utilities import SQLDatabase
from sqlalchemy import create_engine

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
    raise ValueError("Missing Supabase credentials in environment variables.")

db: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("Missing DATABASE_URL in environment variables.")

engine = create_engine(DATABASE_URL)
sql_db = SQLDatabase(engine)
