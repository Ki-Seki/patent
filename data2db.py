import argparse
import csv
import datetime

from dataclasses import dataclass

from bs4 import BeautifulSoup
from tqdm import tqdm

from db import SessionLocal, engine
from db.log import get_logger
from db.models import Base, Citation, Patent


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


def parse_abstract(raw_abstract: str) -> str:
    return BeautifulSoup(raw_abstract, "lxml").get_text(separator="", strip=True)


def simplify_row(row: dict[str], field: DataField) -> dict[str]:
    """简化行数据，保留必要的字段"""
    return {
        field.publication_number: row[field.publication_number].strip(),
        field.publication_date: row[field.publication_date].strip(),
        field.patent_office: row[field.patent_office].strip(),
        field.application_filing_date: row[field.application_filing_date].strip(),
        field.applicants_bvd_id_numbers: row[field.applicants_bvd_id_numbers].strip(),
        field.backward_citations: row[field.backward_citations].strip(),
        field.forward_citations: row[field.forward_citations].strip(),
        field.abstract: parse_abstract(row[field.abstract]),
    }


def import_patents_from_csv(csv_file_path: str, field: DataField, log_interval: int):
    """从CSV文件导入专利数据"""

    db = SessionLocal()

    try:
        with open(csv_file_path, encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)

            patent_count = 0
            citation_count = 0

            last_publication_number = ""
            for idx, row in tqdm(enumerate(reader), desc="导入专利数据到数据库中"):
                if idx % log_interval == 0:
                    logger.debug(f"当前处理第 {idx} 行: {simplify_row(row, field)}")

                curr_publication_number = row[field.publication_number].strip()

                # 该新的专利号的导入了
                if curr_publication_number != "":
                    # 1. 提交上一批专利信息
                    db.commit()

                    # 2. 更新上一个专利号
                    last_publication_number = curr_publication_number

                    # 3. 检查当前专利是否已存在
                    if db.query(Patent).filter(Patent.publication_number == curr_publication_number).first():
                        logger.info(f"专利 {curr_publication_number} 已存在，跳过")
                        continue

                    # 4. 创建当前专利记录
                    patent = Patent(
                        publication_number=curr_publication_number,
                        publication_date=parse_date(row[field.publication_date].strip()),
                        patent_office=row[field.patent_office].strip(),
                        application_filing_date=parse_date(row[field.application_filing_date].strip()),
                        applicants_bvd_id_numbers=row[field.applicants_bvd_id_numbers].strip(),
                        abstract=parse_abstract(row[field.abstract]),
                    )
                    db.add(patent)
                    patent_count += 1

                    # 5. 日志输出
                    if patent_count % log_interval == 0:
                        logger.info(
                            f"已导入 {patent_count} 条专利记录，{citation_count} 条引用关系。注意：由于本行的引用关系还未添加，所以这里的引用数可能少最多 2 条。"
                        )

                if row[field.forward_citations].strip() != "":
                    f_citation = Citation(
                        citing_patent=row[field.forward_citations].strip(),
                        cited_patent=last_publication_number,
                        similarity=None,
                    )
                    if (
                        not db.query(Citation)
                        .filter(
                            Citation.citing_patent == f_citation.citing_patent,
                            Citation.cited_patent == f_citation.cited_patent,
                        )
                        .first()
                    ):
                        db.add(f_citation)
                        citation_count += 1

                if row[field.backward_citations].strip() != "":
                    b_citation = Citation(
                        citing_patent=last_publication_number,
                        cited_patent=row[field.backward_citations].strip(),
                        similarity=None,
                    )
                    if (
                        not db.query(Citation)
                        .filter(
                            Citation.citing_patent == b_citation.citing_patent,
                            Citation.cited_patent == b_citation.cited_patent,
                        )
                        .first()
                    ):
                        db.add(b_citation)
                        citation_count += 1

            # 提交剩余的记录
            db.commit()
            logger.info(f"导入完成！共导入 {patent_count} 条专利记录，{citation_count} 条引用关系")

    except Exception as e:
        db.rollback()
        logger.error(f"导入过程中发生错误: {e}")
        raise
    finally:
        db.close()


def get_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="从CSV文件导入专利数据")
    parser.add_argument("--csv-file", type=str, required=True, help="CSV文件路径")
    parser.add_argument("--log-interval", type=int, required=True, help="日志输出间隔")

    # 下面是各个列明的映射
    parser.add_argument("--publication-number", type=str, required=True)
    parser.add_argument("--publication-date", type=str, required=True)
    parser.add_argument("--patent-office", type=str, required=True)
    parser.add_argument("--application-filing-date", type=str, required=True)
    parser.add_argument("--applicants-bvd-id-numbers", type=str, required=True)
    parser.add_argument("--backward-citations", type=str, required=True)
    parser.add_argument("--forward-citations", type=str, required=True)
    parser.add_argument("--abstract", type=str, required=True)

    return parser.parse_args()


if __name__ == "__main__":
    args = get_args()
    logger.info(f"执行导入操作，参数：{args}")

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

    import_patents_from_csv(args.csv_file, field, args.log_interval)
