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
    parser.add_argument("--commit-interval", type=int, required=True, help="Number of records to commit at once.")
    args = parser.parse_args()
    logger.info(f"Starting to add listed company information. {args=}")

    # Create tables if they do not exist
    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    count = 0
    with open(args.csv_file, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        p_bar: tqdm = tqdm(desc="Processing rows")
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
                    patent.listed_company = True  # type: ignore[assignment]
                    session.add(patent)
                    count += 1
                else:
                    logger.warning(f"Patent {publication_number} not found in the database.")

                if count > 0 and count % args.commit_interval == 0:
                    session.commit()
                    logger.info(f"Committed {count} updates.")

            except Exception as e:
                logger.error(e)
                session.rollback()
            p_bar.update(1)
        p_bar.close()

    session.commit()
    session.close()
    logger.info("Listed company information updated successfully.")
