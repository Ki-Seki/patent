import os

import dotenv

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .log import get_logger


logger = get_logger(__name__)

dotenv.load_dotenv()

DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL") or ""
logger.info(f"Connecting to database at {DATABASE_URL}")

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()
