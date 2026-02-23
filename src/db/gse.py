"""Gene Expression Omnibus Series (GSE) data model."""

from dataclasses import dataclass, field
from typing import Optional

from src.db.mapper_registry import mapper_registry

from sqlalchemy import Index, Integer, PrimaryKeyConstraint, REAL, Text, Column


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
