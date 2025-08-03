import argparse
import csv
import datetime

from dataclasses import dataclass

from . import SessionLocal, engine
from .log import get_logger
from .models import Base, Citation, Patent


logger = get_logger(__name__)


@dataclass
class DataField:
    publication_number: str
    publication_date: str
    patent_office: str
    application_filing_date: str
    applicants_bvd_id_numbers: str
    backward_citations: str
    forward_citations: str
    abstract: str


def parse_date(date_str: str) -> datetime.date:
    return datetime.datetime.strptime(date_str.strip(), "%d/%m/%Y").date()


def import_patents_from_csv(csv_file_path: str, field: DataField):
    """从CSV文件导入专利数据"""

    db = SessionLocal()

    try:
        with open(csv_file_path, encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)

            patent_count = 0
            citation_count = 0

            publication_number = ""
            for row in reader:
                if row[field.publication_number].strip() != "":
                    # 遇到新的专利号，提交上一批专利信息
                    db.commit()
                    logger.info(f"已处理 {patent_count} 条专利记录")

                    publication_number = row[field.publication_number].strip()

                # 检查专利是否已存在
                existing_patent = db.query(Patent).filter(Patent.publication_number == publication_number).first()

                if existing_patent:
                    logger.info(f"专利 {publication_number} 已存在，跳过")
                    continue

                # 创建专利记录
                patent = Patent(
                    publication_number=publication_number,
                    publication_date=parse_date(row[field.publication_date].strip()),
                    patent_office=row[field.patent_office].strip(),
                    application_filing_date=parse_date(row[field.application_filing_date].strip()),
                    applicants_bvd_id_numbers=row[field.applicants_bvd_id_numbers].strip(),
                    abstract=row[field.abstract].strip(),
                )

                db.add(patent)
                patent_count += 1

                if row[field.forward_citations].strip() != "":
                    citation = Citation(
                        citing_patent=row[field.forward_citations].strip(),
                        cited_patent=publication_number,
                        similarity=None,
                    )
                    db.add(citation)
                    citation_count += 1

                if row[field.backward_citations].strip() != "":
                    citation = Citation(
                        citing_patent=publication_number,
                        cited_patent=row[field.backward_citations].strip(),
                        similarity=None,
                    )
                    db.add(citation)
                    citation_count += 1

            # 提交剩余的记录
            db.commit()
            logger.info(f"导入完成！共导入 {patent_count} 条专利记录，{citation_count} 条引用关系")

    except Exception as e:
        db.rollback()
        logger.info(f"导入过程中发生错误: {e}")
        raise
    finally:
        db.close()


def get_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="从CSV文件导入专利数据")
    parser.add_argument("csv_file_path", type=str, help="CSV文件路径")

    parser.add_argument("publication_number", type=str, help="Publication Number列名")
    parser.add_argument("publication_date", type=str, help="Publication Date列名")
    parser.add_argument("patent_office", type=str, help="Patent Office列名")
    parser.add_argument("application_filing_date", type=str, help="Application/Filing Date列名")
    parser.add_argument("applicants_bvd_id_numbers", type=str, help="Applicant(s) BvD ID Number(s)列名")
    parser.add_argument("backward_citations", type=str, help="Backward Citations列名")
    parser.add_argument("forward_citations", type=str, help="Forward Citations列名")
    parser.add_argument("abstract", type=str, help="Abstract列名")

    return parser.parse_args()


if __name__ == "__main__":
    args = get_args()

    Base.metadata.create_all(bind=engine)

    field = DataField(
        publication_number=args.publication_number,
        publication_date=args.publication_date,
        patent_office=args.patent_office,
        application_filing_date=args.application_filing_date,
        applicants_bvd_id_numbers=args.applicants_bvd_id_numbers,
        backward_citations=args.backward_citations,
        forward_citations=args.forward_citations,
        abstract=args.abstract,
    )

    import_patents_from_csv(args.csv_file_path, field)
