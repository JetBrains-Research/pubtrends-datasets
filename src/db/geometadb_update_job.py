import datetime
from dataclasses import dataclass, field
from typing import Optional, List

from sqlalchemy import Column, Index, Integer, DateTime, ForeignKey, String, CheckConstraint
from sqlalchemy.orm import relationship

from src.db.mapper_registry import mapper_registry


@mapper_registry.mapped
@dataclass
class GEOmetadbUpdateJobAssociation:
    __tablename__ = "gse_update_association"
    __sa_dataclass_metadata_key__ = "sa"

    update_id: int = field(
        init=False,
        metadata={"sa": Column(Integer, ForeignKey("gse_update.id"), primary_key=True)}
    )
    gse_acc: str = field(default=None,
                         metadata={"sa": Column(String, primary_key=True)}
                         )
    status: str = field(default="pending", metadata={
        "sa": Column(String, CheckConstraint('status IN ("pending", "failed", "successful")'))})


@mapper_registry.mapped
@dataclass
class GEOmetadbUpdateJob:
    __tablename__ = 'gse_update'
    __table_args__ = (
        Index('gse_update_id_idx', 'id'),
    )
    __sa_dataclass_metadata_key__ = "sa"

    id: int = field(default=None, metadata={"sa": Column(Integer, primary_key=True, autoincrement=True)})
    date: Optional[datetime.datetime] = field(default=None, metadata={"sa": Column(DateTime)})
    status: str = field(default="in_progress", metadata={
        "sa": Column(String, CheckConstraint('status IN ("in_progress", "cancelled", "failed", "successful")'))})
    last_update_date_start: Optional[datetime.datetime] = field(default=None, metadata={"sa": Column(DateTime)})
    last_update_date_end: Optional[datetime.datetime] = field(default=None, metadata={"sa": Column(DateTime)})
    updated_gses: List[GEOmetadbUpdateJobAssociation] = field(
        default_factory=list,
        metadata={"sa": relationship("GEOmetadbUpdateJobAssociation")}
    )
