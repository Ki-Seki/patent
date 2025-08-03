from sqlalchemy import DECIMAL, Column, Date, ForeignKey, String, Text

from . import Base


class Patent(Base):
    __tablename__ = "patent"

    publication_number = Column(String(50), primary_key=True)
    publication_date = Column(Date)
    patent_office = Column(String(25))
    application_filing_date = Column(Date)
    applicants_bvd_id_numbers = Column(String(100))
    abstract = Column(Text)


class Citation(Base):
    __tablename__ = "citation"

    citing_patent = Column(String(50), ForeignKey("patent.publication_number"), primary_key=True)
    cited_patent = Column(String(50), ForeignKey("patent.publication_number"), primary_key=True)
    similarity = Column(DECIMAL)
