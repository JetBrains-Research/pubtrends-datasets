"""Gene Expression Omnibus Series (GSE) data model."""
from dataclasses import dataclass, field
from typing import Optional, List

from sqlalchemy.ext.associationproxy import association_proxy, AssociationProxy
from sqlalchemy.orm import relationship

from src.db.models.gse_gsm import GSE_GSM
from src.db.models.mapper_registry import mapper_registry

from sqlalchemy import Index, Integer, PrimaryKeyConstraint, REAL, Text, Column

SUPERSERIES_SUMMARY = "This SuperSeries is composed of the SubSeries listed below."


@mapper_registry.mapped
@dataclass
class GSE:
    """Gene Expression Omnibus Series (GSE) data model."""
    __tablename__ = 'gse'
    __table_args__ = (
        PrimaryKeyConstraint('gse', name='pk_gse'),
        Index('gse_acc_idx', 'gse')
    )
    __sa_dataclass_metadata_key__ = "sa"

    ID: Optional[float] = field(default=None, metadata={"sa": Column(REAL)})
    title: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    gse: Optional[str] = field(default=None, metadata={"sa": Column(Text, primary_key=True)})
    status: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    submission_date: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    last_update_date: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    pubmed_id: Optional[int] = field(default=None, metadata={"sa": Column(Integer)})
    summary: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    type: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    contributor: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    web_link: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    overall_design: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    repeats: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    repeats_sample_list: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    variable: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    variable_description: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    contact: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    supplementary_file: Optional[str] = field(default=None, metadata={"sa": Column(Text)})

    gse_gsm_links: List["GSE_GSM"] = field(default_factory=list,
                                           metadata={"sa": relationship("GSE_GSM", viewonly=True)})
    gsm_ids: AssociationProxy[List[str]] = field(default_factory=list,
                                                 metadata={"sa": association_proxy("gse_gsm_links", "gsm")})

    def is_superseries(self):
        return self.summary == SUPERSERIES_SUMMARY


@dataclass()
class GSE_DTO:
    ID: Optional[float]
    title: Optional[str]
    gse: Optional[str]
    status: Optional[str]
    submission_date: Optional[str]
    last_update_date: Optional[str]
    pubmed_id: Optional[int]
    summary: Optional[str]
    type: Optional[str]
    contributor: Optional[str]
    web_link: Optional[str]
    overall_design: Optional[str]
    repeats: Optional[str]
    repeats_sample_list: Optional[str]
    variable: Optional[str]
    variable_description: Optional[str]
    contact: Optional[str]
    supplementary_file: Optional[str]
    gsm_ids: List[str]

    def __init__(self, gse: GSE):
        self.ID = gse.ID
        self.title = gse.title
        self.gse = gse.gse
        self.status = gse.status
        self.submission_date = gse.submission_date
        self.last_update_date = gse.last_update_date
        self.pubmed_id = gse.pubmed_id
        self.summary = gse.summary
        self.type = gse.type
        self.contributor = gse.contributor
        self.web_link = gse.web_link
        self.overall_design = gse.overall_design
        self.repeats = gse.repeats
        self.repeats_sample_list = gse.repeats_sample_list
        self.variable = gse.variable
        self.variable_description = gse.variable_description
        self.contact = gse.contact
        self.supplementary_file = gse.supplementary_file
        self.gsm_ids = list(gse.gsm_ids)
