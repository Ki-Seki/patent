# TODO: add listed company support
import argparse
import csv
import datetime

from dataclasses import dataclass
from functools import lru_cache

from lxml import html
from more_itertools import peekable
from tqdm import tqdm

from db import SessionLocal, engine
from db.log import get_logger
from db.models import Base, Patent


csv.field_size_limit(10**9)

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


@lru_cache(maxsize=512)
def parse_abstract(raw_abstract: str) -> str:
    try:
        tree = html.fromstring(raw_abstract)
        return tree.text_content().strip()  # type: ignore[attr-defined]
    except Exception:
        return raw_abstract.strip()


def simplify_row(row: dict[str, str], field: DataField) -> str:
    """简化行数据，保留必要的字段"""
    simplified = {
        field.publication_number: row[field.publication_number].strip(),
        field.publication_date: row[field.publication_date].strip(),
        field.patent_office: row[field.patent_office].strip(),
        field.application_filing_date: row[field.application_filing_date].strip(),
        field.applicants_bvd_id_numbers: row[field.applicants_bvd_id_numbers].strip(),
        field.backward_citations: row[field.backward_citations].strip(),
        field.forward_citations: row[field.forward_citations].strip(),
        field.abstract: parse_abstract(row[field.abstract])[:50],
    }
    return ", ".join(v for v in simplified.values())


def import_patents_from_csv(csv_file_path: str, field: DataField, log_interval: int):
    """从CSV文件导入专利数据"""

    db = SessionLocal()
    file = open(csv_file_path, encoding="utf-8-sig")  # noqa: SIM115
    p_bar: tqdm = tqdm(desc="导入专利数据")
    try:
        reader = peekable(csv.DictReader(file))
        patent_count = 0
        while first_row := next(reader, None):
            # 跳过最初的无专利行
            if first_row[field.publication_number].strip() == "":
                logger.info(f"跳过无专利后继引用行：{simplify_row(first_row, field)}")
                continue

            # 跳过重复专利
            pub_num = first_row[field.publication_number].strip()
            if db.query(Patent).filter(Patent.publication_number == pub_num).first():
                logger.warning(f"跳过重复专利：{simplify_row(first_row, field)}")
                while row := reader.peek(None):
                    if row[field.publication_number].strip() != "":
                        break  # 遇到新专利行了，退出内层循环
                    else:
                        tmp_row = next(reader)  # 消耗该行
                        logger.info("跳过重复专利后继引用行")
                continue

            # 完整得到一条专利，保存到 first_row 中
            logger.info(f"处理专利行：{simplify_row(first_row, field)}")
            while row := reader.peek(None):
                if row[field.publication_number].strip() != "":
                    break  # 遇到新专利行了，退出内层循环
                else:
                    tmp_row = next(reader)  # 消耗该行
                    logger.info(f"处理后继引用行：{simplify_row(tmp_row, field)}")

                    f_citation = row[field.forward_citations].strip()
                    if f_citation not in first_row[field.forward_citations]:
                        first_row[field.forward_citations] += f",{f_citation}"
                    b_citation = row[field.backward_citations].strip()
                    if b_citation not in first_row[field.backward_citations]:
                        first_row[field.backward_citations] += f",{b_citation}"

            # 添加该专利到数据库
            try:
                patent = Patent(
                    publication_number=first_row[field.publication_number].strip(),
                    publication_date=parse_date(first_row[field.publication_date].strip()),
                    patent_office=first_row[field.patent_office].strip(),
                    application_filing_date=parse_date(first_row[field.application_filing_date].strip()),
                    applicants_bvd_id_numbers=first_row[field.applicants_bvd_id_numbers].strip(),
                    backward_citations=first_row[field.backward_citations].strip(),
                    forward_citations=first_row[field.forward_citations].strip(),
                    abstract=parse_abstract(first_row[field.abstract]),
                )
                db.add(patent)
                db.commit()
                patent_count += 1
            except Exception as e:
                db.rollback()
                logger.error(f"跳过完整专利 {simplify_row(first_row, field)} - {e}")
                continue

            # 定期日志输出
            if patent_count % log_interval == 0:
                logger.info(f"已导入 {patent_count} 条专利记录")

            p_bar.update(1)
    except Exception as e:
        db.rollback()
        logger.error(f"导入过程中发生错误：{e}")
        raise
    finally:
        p_bar.close()
        file.close()
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
