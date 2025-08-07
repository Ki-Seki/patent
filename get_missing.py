# TODO：有错误需要改，只算上市公司的
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
    total_processed = 0
    total_missing = 0

    while True:
        # 批量读取
        patents = (
            db.query(Patent.publication_number, Patent.backward_citations, Patent.forward_citations)
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
            all_citations.update(extract_citation_nums(row.forward_citations))

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

            logger.info(f"{total_missing} / {total_processed} 专利缺失引用已收集")

    db.close()


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    logger.info("Starting to collect missing citations...")
    collect_missing_citations()
    logger.info("Finished collecting missing citations.")
