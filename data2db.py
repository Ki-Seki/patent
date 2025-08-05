import argparse
import csv
import datetime

from dataclasses import dataclass

from bs4 import BeautifulSoup
from tqdm import tqdm

from db import SessionLocal, engine
from db.log import get_logger
from db.models import Base, Patent


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


def simplify_row(row: dict[str, str], field: DataField) -> dict[str, str]:
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
            patent = None
            for idx, row in tqdm(enumerate(reader), desc="导入专利数据到数据库中"):                
                # 每log_interval条记录输出一次日志
                if (idx+1) % log_interval == 0:
                    logger.info(f"正在处理CSV第 {idx+1} 行：{list(simplify_row(row, field).values())}")

                # 遇到新的专利行
                if row[field.publication_number].strip() != "":
                    # 1. 提交上一个patent，除去第一个
                    if patent is not None:
                        db.add(patent)
                        db.commit()
                        patent_count += 1
                        patent = None

                    # 2. 检查是否已经存在该专利
                    pub_num = row[field.publication_number].strip()
                    if db.query(Patent).filter(Patent.publication_number == pub_num).first():
                        logger.info(f"跳过：专利 {pub_num} 已存在")
                        continue

                    # 3. 添加当前行的专利信息
                    patent = Patent(
                        publication_number=row[field.publication_number].strip(),
                        publication_date=parse_date(row[field.publication_date].strip()),
                        patent_office=row[field.patent_office].strip(),
                        application_filing_date=parse_date(row[field.application_filing_date].strip()),
                        applicants_bvd_id_numbers=row[field.applicants_bvd_id_numbers].strip(),
                        backward_citations=row[field.backward_citations].strip(),
                        forward_citations=row[field.forward_citations].strip(),
                        abstract=parse_abstract(row[field.abstract]),
                    )

                # 仅包含引用信息的行
                else:
                    if patent is None:
                        logger.info(f"跳过：可能是没有专利的后继引用行，或者是重复的专利的后继引用行")
                        continue

                    f_citation = row[field.forward_citations].strip()
                    if f_citation and f_citation not in patent.forward_citations:
                        patent.forward_citations += f",{f_citation}"  # type: ignore[assignment]
                    b_citation = row[field.backward_citations].strip()
                    if b_citation and b_citation not in patent.backward_citations:
                        patent.backward_citations += f",{b_citation}"  # type: ignore[assignment]

            # 提交剩余的记录
            db.commit()
            logger.info(f"导入完成！共导入 {patent_count} 条专利记录")

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
