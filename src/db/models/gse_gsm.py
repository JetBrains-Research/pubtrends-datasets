from dataclasses import dataclass, field

from sqlalchemy import Index, PrimaryKeyConstraint, Text, Column, ForeignKey

from src.db.models.mapper_registry import mapper_registry


@mapper_registry.mapped
@dataclass
class GSE_GSM:
    __tablename__ = 'gse_gsm'
    __table_args__ = (
        PrimaryKeyConstraint('gse', 'gsm', name='pk_gse'),
        Index('gse_gsm_idx1', 'gse'),
        Index('gse_gsm_idx2', 'gsm')
    )
    __sa_dataclass_metadata_key__ = "sa"

    gse: str = field(metadata={"sa": Column(Text, ForeignKey('gse.gse'))})
    gsm: str = field(metadata={"sa": Column(Text, ForeignKey('gsm.gsm'))})
