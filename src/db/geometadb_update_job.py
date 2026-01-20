import datetime
from dataclasses import dataclass, field
from typing import Optional, List

from src.db.mapper_registry import mapper_registry

from sqlalchemy import Column, Index, Integer, PrimaryKeyConstraint, DateTime, ForeignKey, String, Boolean
from sqlalchemy.orm import relationship


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


@mapper_registry.mapped
@dataclass
class GEOmetadbUpdateJob:
    __tablename__ = 'gse_update'
    __table_args__ = (
        PrimaryKeyConstraint('id', name='pk_gse_update_id'),
        Index('gse_update_id_idx', 'id')
    )
    __sa_dataclass_metadata_key__ = "sa"

    id: int = field(default=None, metadata={"sa": Column(Integer)})
    date: Optional[datetime.datetime] = field(default=None, metadata={"sa": Column(DateTime)})
    completed: bool = field(default=False, metadata={"sa": Column(Boolean)})
    last_update_date_start: Optional[datetime.datetime] = field(default=None, metadata={"sa": Column(DateTime)})
    last_update_date_end: Optional[datetime.datetime] = field(default=None, metadata={"sa": Column(DateTime)})
    updated_gses: List[GEOmetadbUpdateJobAssociation] = field(
        default_factory=list,
        metadata={"sa": relationship("GEOmetadbUpdateJobAssociation")}
    )
