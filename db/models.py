from sqlalchemy import DECIMAL, Column, Date, Index, PrimaryKeyConstraint, String, Text

from . import Base


class Patent(Base):
    __tablename__ = "patent"

    publication_number = Column(String(20), primary_key=True)
    publication_date = Column(Date)
    patent_office = Column(String(10))
    application_filing_date = Column(Date)
    applicants_bvd_id_numbers = Column(String(40))
    abstract = Column(Text)


class Citation(Base):
    __tablename__ = "citation"

    citing_patent = Column(String(20), primary_key=True)
    cited_patent = Column(String(20), primary_key=True)
    similarity = Column(DECIMAL)

    __table_args__ = (
        PrimaryKeyConstraint("citing_patent", "cited_patent"),
        Index("ix_cited_patent", "cited_patent"),
    )
