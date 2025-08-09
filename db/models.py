from sqlalchemy import DECIMAL, Boolean, Column, Date, ForeignKey, String, Text

from . import Base


class Patent(Base):
    __tablename__ = "patent"

    publication_number = Column(String(20), primary_key=True)
    publication_date = Column(Date)
    patent_office = Column(String(10))
    application_filing_date = Column(Date)
    applicants_bvd_id_numbers = Column(String(40))
    backward_citations = Column(Text)
    forward_citations = Column(Text)
    abstract = Column(Text)
    # 下面的字段不存在于原始csv数据中
    listed_company = Column(Boolean, default=None)  # 是否上市公司


class ExtendedInfo(Base):
    __tablename__ = "extended_info"

    publication_number = Column(String(20), ForeignKey("patent.publication_number"), primary_key=True)
    b1f0_patents = Column(Text)
    b1f1_patents = Column(Text)
    b0f1_patents = Column(Text)


class PatentMatrix(Base):
    __tablename__ = "patent_matrix"

    small_patent = Column(String(20), ForeignKey("patent.publication_number"), primary_key=True)
    big_patent = Column(String(20), ForeignKey("patent.publication_number"), primary_key=True)
    similarity = Column(DECIMAL)


class PatentMissing(Base):
    __tablename__ = "patent_missing"

    publication_number = Column(String(20), primary_key=True)
