from datetime import date
from functools import lru_cache
from typing import Literal

from sqlalchemy.orm import Session
from tqdm import tqdm

from db import SessionLocal, engine
from db.log import get_logger
from db.models import Base, ExtendedInfo, Patent


logger = get_logger(__name__)


def get_bxfx(db: Session, focus_patent: str) -> tuple[set[str], set[str], set[str]]:
    """
    给定焦点专利号，返回b1f0, b1f1, b0f1专利列表
    """

    @lru_cache(maxsize=204800)
    def get_patent_date(patent: str) -> date | None:
        """
        获取专利的发布日期
        """
        result = db.query(Patent.publication_date).filter(Patent.publication_number == patent).first()
        return result[0] if result else None

    @lru_cache(maxsize=204800)
    def get_citations(patent: str, direction: Literal["backward", "forward"]) -> set[str]:
        """
        获取专利的引用
        """
        if not db.query(Patent).filter(Patent.publication_number == patent).first():
            raise ValueError(f"专利 {patent} 不存在")
        if direction == "backward":
            citations_str = db.query(Patent.backward_citations).filter(Patent.publication_number == patent).first()
        else:
            citations_str = db.query(Patent.forward_citations).filter(Patent.publication_number == patent).first()

        return set(citations_str[0].split(",")) if citations_str and citations_str[0] else set()

    backward_patents = get_citations(focus_patent, "backward")
    forward_patents = get_citations(focus_patent, "forward")

    forward_patents_of_backward_patents = set()
    for backward_patent in backward_patents:
        forward_patents_of_backward_patents.update(get_citations(backward_patent, "forward"))

    b0f1 = forward_patents - forward_patents_of_backward_patents
    b1f1 = forward_patents & forward_patents_of_backward_patents

    # 获取焦点专利的发布日期
    focus_patent_date = get_patent_date(focus_patent)

    # 对于b1f0专利，需要过滤掉发布日期早于或等于焦点专利的专利
    potential_b1f0 = forward_patents_of_backward_patents - forward_patents - {focus_patent}
    b1f0 = set()

    if focus_patent_date:
        for patent in potential_b1f0:
            patent_date = get_patent_date(patent)
            if patent_date and patent_date > focus_patent_date:
                b1f0.add(patent)
    else:
        # 如果焦点专利没有日期信息，保持原有逻辑
        b1f0 = potential_b1f0

    return b0f1, b1f1, b1f0


if __name__ == "__main__":
    logger.info("开始计算b1f0, b1f1, b0f1")

    # Create tables if they do not exist
    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    patent_count = session.query(Patent).filter(Patent.listed_company).count()
    logger.info(f"待处理专利数量: {patent_count}")

    # 分批遍历所有上市公司专利
    batch_size = 10000
    with tqdm(total=patent_count) as pbar:
        offset = 0
        while True:
            patents = session.query(Patent).filter(Patent.listed_company).offset(offset).limit(batch_size).all()
            if not patents:
                break

            for patent in patents:
                pbar.update(1)
                publication_number = patent.publication_number
                try:
                    b1f0_patents, b1f1_patents, b0f1_patents = get_bxfx(session, publication_number)  # type: ignore
                except ValueError as e:
                    logger.error(f"跳过专利 {publication_number}: {e}")
                    continue
                info = ExtendedInfo(
                    publication_number=publication_number,
                    b1f0_patents=",".join(b1f0_patents),
                    b1f1_patents=",".join(b1f1_patents),
                    b0f1_patents=",".join(b0f1_patents),
                )
                session.add(info)

            session.commit()  # 批量提交
            offset += batch_size
            logger.info(f"已处理 {offset} / {patent_count} 专利")

    session.close()
    logger.info("计算完成")
