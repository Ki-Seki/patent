from functools import lru_cache
from typing import Literal

from sqlalchemy.orm import Session
from tqdm import tqdm

from db import SessionLocal, engine
from db.log import get_logger
from db.models import Base, ExtendedInfo, Patent


logger = get_logger(__name__)


@lru_cache(maxsize=512)
def get_citations(db: Session, patent: str, direction: Literal["backward", "forward"]) -> set[str]:
    """
    获取专利的引用
    """
    if direction == "backward":
        citations_str = db.query(Patent.backward_citations).filter(Patent.publication_number == patent).first()
    else:
        citations_str = db.query(Patent.forward_citations).filter(Patent.publication_number == patent).first()

    return set(citations_str[0].split(",")) if citations_str else set()


def get_bxfx(db: Session, focus_patent: str) -> tuple[set[str], set[str], set[str]]:
    """
    给定焦点专利号，返回b1f0, b1f1, b0f1专利列表
    """
    backward_patents = get_citations(db, focus_patent, "backward")
    forward_patents = get_citations(db, focus_patent, "forward")

    forward_patents_of_backward_patents = set()
    for backward_patent in backward_patents:
        forward_patents_of_backward_patents.update(get_citations(db, backward_patent, "forward"))

    b0f1 = forward_patents - forward_patents_of_backward_patents
    b1f1 = forward_patents & forward_patents_of_backward_patents
    b1f0 = forward_patents_of_backward_patents - forward_patents - {focus_patent}

    return b0f1, b1f1, b1f0


if __name__ == "__main__":
    logger.info("开始计算b1f0, b1f1, b0f1")

    # Create tables if they do not exist
    Base.metadata.create_all(bind=engine)

    session = SessionLocal()

    # 循环遍历patent表里的每一行
    patent_count = session.query(Patent).filter(Patent.listed_company == True).count()
    for patent in tqdm(session.query(Patent).filter(Patent.listed_company == True).all(), total=patent_count):
        publication_number = patent.publication_number
        b1f0_patents, b1f1_patents, b0f1_patents = get_bxfx(session, publication_number)  # type: ignore
        info = ExtendedInfo(
            publication_number=publication_number,
            b1f0_patents=",".join(b1f0_patents),
            b1f1_patents=",".join(b1f1_patents),
            b0f1_patents=",".join(b0f1_patents),
        )
        session.add(info)
        session.commit()

    session.close()
    logger.info("计算完成")
