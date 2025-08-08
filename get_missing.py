from sqlalchemy.dialects.mysql import insert

from db import SessionLocal, engine
from db.log import get_logger
from db.models import Base, Patent, PatentMissing


logger = get_logger(__name__)


def extract_citation_nums(citation_str):
    if not citation_str:
        return []
    return [c.strip() for c in citation_str.split(",") if c.strip()]


def collect_missing_citations(batch_size: int = 100000):
    db = SessionLocal()
    offset = 0
    total_processed = 0  # 已处理的专利数量
    total_missing = 0  # 已收集的缺失引用数量，未去重
    total_citations = 0  # 所有专利的前后引用数量合，未去重

    while True:
        # 批量读取上市公司的专利
        patents = (
            db.query(Patent.publication_number, Patent.backward_citations, Patent.forward_citations)
            .filter(Patent.listed_company == 1)
            .offset(offset)
            .limit(batch_size)
            .all()
        )

        if not patents:
            break

        offset += batch_size
        total_processed += len(patents)

        # 收集所有的引用号
        all_citations = set()
        for row in patents:
            all_citations.update(extract_citation_nums(row.backward_citations))
        total_citations += len(all_citations)

        if not all_citations:
            continue

        # 查询哪些在专利表中
        chunk_size = 10000  # 避免 SQL 过长
        existing_citations: set[str] = set()
        citation_list = list(all_citations)
        for i in range(0, len(citation_list), chunk_size):
            chunk = citation_list[i : i + chunk_size]
            rows = db.query(Patent.publication_number).filter(Patent.publication_number.in_(chunk)).all()
            existing_citations.update(r[0] for r in rows)

        # 计算缺失
        missing_citations = all_citations - existing_citations

        # 批量插入 missing 表，防止重复插入
        if missing_citations:
            insert_stmt = insert(PatentMissing).values([{"publication_number": pub} for pub in missing_citations])
            on_duplicate_stmt = insert_stmt.prefix_with("IGNORE")
            db.execute(on_duplicate_stmt)
            db.commit()

            total_missing += len(missing_citations)

            logger.warning(
                f"{total_missing} / {total_citations} 上市公司专利缺失引用已收集，来自 {total_processed} 条专利"
            )

    db.close()


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    logger.info("Starting to collect missing citations for listed companies...")
    collect_missing_citations()
    logger.info("Finished collecting missing citations for listed companies.")
