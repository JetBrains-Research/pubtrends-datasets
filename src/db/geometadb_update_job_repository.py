import datetime
import logging
from typing import List, Optional
import os

from sqlalchemy import select, create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session

from src.db.geometadb_update_job import GEOmetadbUpdateJob, GEOmetadbUpdateJobAssociation

logger = logging.getLogger(__name__)


class GEOmetadbUpdateJobRepository:
    def __init__(self, geometadb_path: str) -> None:
        if not os.path.isfile(geometadb_path):
            raise RuntimeError(f"Geometadb file {geometadb_path} does not exist")
        if not os.access(geometadb_path, os.W_OK):
            raise RuntimeError(f"Geometadb file {geometadb_path} is not writable")
        self.engine = create_engine(f"sqlite:///{geometadb_path}")
        self.async_engine = create_async_engine(f"sqlite+aiosqlite:///{geometadb_path}", future=True, echo=False)

    def create_update_job(self, updated_gse_accessions: List[str], last_update_date_start: datetime.datetime, last_update_date_end: datetime.datetime) -> GEOmetadbUpdateJob:
        """
        Creates a new update job record and links it to the updated GSE accessions.
        :param updated_gse_accessions: List of GEO accessions for the updated datasets.
        :param last_update_date_start: Earliest update date for the datasets that were downloaded.
        :param last_update_date_end: Latest update date for the datasets that were downloaded.
        """
        try:
            with Session(self.engine, expire_on_commit=False) as session:
                update_job = GEOmetadbUpdateJob(date=datetime.datetime.now(), last_update_date_start=last_update_date_start, last_update_date_end=last_update_date_end)
                for acc in updated_gse_accessions:
                    update_job.updated_gses.append(GEOmetadbUpdateJobAssociation(gse_acc=acc))
                assert update_job is not None
                session.add(update_job)
                session.commit()
                return update_job
        except SQLAlchemyError as e:
            logger.exception(f"Failed to create update job:")
            raise e

    def get_job_by_id(self, job_id: int) -> Optional[GEOmetadbUpdateJob]:
        """Retrieves a job record by its job_id string."""
        try:
            with Session(self.engine) as session:
                stmt = select(GEOmetadbUpdateJob).where(GEOmetadbUpdateJob.id == job_id)
                return session.scalars(stmt).first()
        except SQLAlchemyError as e:
            logger.exception(f"Failed to retrieve job {job_id}:")
            raise e

    def mark_job_complete(self, job_id: int) -> None:
        try:
            with Session(self.engine) as session:
                stmt = select(GEOmetadbUpdateJob).where(GEOmetadbUpdateJob.id == job_id)
                job = session.scalars(stmt).first()
                job.completed = True
                session.commit()
        except SQLAlchemyError as e:
            logger.exception(f"Failed to mark job {job_id} as complete:")
            raise e
