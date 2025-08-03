import os

import dotenv

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


dotenv.load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL") or ""

engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()
