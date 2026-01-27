import datetime
from dataclasses import dataclass, field
from typing import Optional, List

from sqlalchemy import Column, Index, Integer, DateTime, ForeignKey, String, CheckConstraint
from sqlalchemy.orm import relationship

from src.db.mapper_registry import mapper_registry


@mapper_registry.mapped
@dataclass
class GSEUpdate:
    __tablename__ = "gse_update"
    __sa_dataclass_metadata_key__ = "sa"

    geometadb_update_job_id: int = field(
        init=False,
        metadata={"sa": Column(Integer, ForeignKey("geometadb_update_job.id"), primary_key=True)}
    )
    gse_acc: str = field(default=None,
                         metadata={"sa": Column(String, primary_key=True)}
                         )
    status: str = field(default="pending", metadata={
        "sa": Column(String, CheckConstraint('status IN ("pending", "failed", "successful")'))})


@mapper_registry.mapped
@dataclass
class GEOmetadbUpdateJob:
    __tablename__ = "geometadb_update_job"
    __table_args__ = (
        Index("geometadb_update_job_id_idx", "id"),
    )
    __sa_dataclass_metadata_key__ = "sa"

    id: int = field(default=None, metadata={"sa": Column(Integer, primary_key=True, autoincrement=True)})
    date: Optional[datetime.datetime] = field(default=None, metadata={"sa": Column(DateTime)})
    status: str = field(default="in_progress", metadata={
        "sa": Column(String, CheckConstraint('status IN ("in_progress", "cancelled", "failed", "successful")'))})
    last_update_date_start: Optional[datetime.datetime] = field(default=None, metadata={"sa": Column(DateTime)})
    last_update_date_end: Optional[datetime.datetime] = field(default=None, metadata={"sa": Column(DateTime)})
    updated_gses: List[GSEUpdate] = field(
        default_factory=list,
        metadata={"sa": relationship("GSEUpdate")}
    )
