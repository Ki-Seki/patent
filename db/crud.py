from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import PatentMatrix


# TODO：废弃
def get_second_level_citations(db: Session, publication_number: str) -> list[str]:
    """
    查询引用了某专利的专利的被引用专利（排除自身）
    """
    first_level = select(PatentMatrix.big_patent).where(PatentMatrix.small_patent == publication_number)
    second_level = (
        db.query(PatentMatrix.small_patent)
        .filter(PatentMatrix.big_patent.in_(first_level))
        .filter(PatentMatrix.small_patent != publication_number)
        .distinct()
    )

    return [row[0] for row in second_level]
