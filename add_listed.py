import argparse
import csv

from tqdm import tqdm

from db import SessionLocal, engine
from db.log import get_logger
from db.models import Base, Patent


logger = get_logger(__name__)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add listed company information to patents.")
    parser.add_argument("--csv-file", type=str, help="Path to the CSV file containing listed company data.")
    parser.add_argument("--publication-number", type=str, required=True, help="Column name for publication number.")
    args = parser.parse_args()
    logger.info(f"Starting to add listed company information. {args=}")

    # Create tables if they do not exist
    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    with open(args.csv_file, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        p_bar = tqdm(desc="Processing rows")
        while True:
            try:
                row = next(reader, None)
                if row is None:
                    break
                publication_number = row[args.publication_number].strip()
                if not publication_number:
                    continue

                patent = session.query(Patent).filter_by(publication_number=publication_number).first()
                if patent:
                    patent.listed_company = True
                    session.add(patent)
                    logger.info(f"Updated listed company for patent {publication_number}.")
                else:
                    logger.warning(f"Patent {publication_number} not found in the database.")
            except Exception as e:
                logger.error(e)

    session.commit()
    session.close()
    logger.info("Listed company information updated successfully.")
