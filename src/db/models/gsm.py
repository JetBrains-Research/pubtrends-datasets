"""Gene Expression Omnibus Sample (GSM) data model."""

from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import Column, Index, PrimaryKeyConstraint, REAL, Text

from src.db.models.mapper_registry import mapper_registry


@mapper_registry.mapped
@dataclass
class GSM:
    """Gene Expression Omnibus Sample (GSM) data model."""
    __tablename__ = 'gsm'
    __table_args__ = (
        PrimaryKeyConstraint('gsm', name='pk_gsm'),
        Index('gsm_acc_idx', 'gsm')
    )
    __sa_dataclass_metadata_key__ = "sa"

    ID: Optional[float] = field(default=None, metadata={"sa": Column(REAL)})
    title: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    gsm: Optional[str] = field(default=None, metadata={"sa": Column(Text, primary_key=True)})
    series_id: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    gpl: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    status: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    submission_date: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    last_update_date: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    type: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    source_name_ch1: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    organism_ch1: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    characteristics_ch1: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    molecule_ch1: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    label_ch1: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    treatment_protocol_ch1: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    extract_protocol_ch1: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    label_protocol_ch1: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    source_name_ch2: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    organism_ch2: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    characteristics_ch2: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    molecule_ch2: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    label_ch2: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    treatment_protocol_ch2: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    extract_protocol_ch2: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    label_protocol_ch2: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    hyb_protocol: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    description: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    data_processing: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    contact: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    supplementary_file: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    data_row_count: Optional[float] = field(default=None, metadata={"sa": Column(REAL)})
    channel_count: Optional[float] = field(default=None, metadata={"sa": Column(REAL)})
