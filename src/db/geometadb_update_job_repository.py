import asyncio
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
MAX_PARALLEL_REQUESTS = 10


class GEOmetadbUpdateJobRepository:
    def __init__(self, geometadb_path: str) -> None:
        if not os.path.isfile(geometadb_path):
            raise RuntimeError(f"Geometadb file {geometadb_path} does not exist")
        if not os.access(geometadb_path, os.W_OK):
            raise RuntimeError(f"Geometadb file {geometadb_path} is not writable")
        self.engine = create_engine(f"sqlite:///{geometadb_path}")
        self.async_engine = create_async_engine(f"sqlite+aiosqlite:///{geometadb_path}", future=True, echo=False)
        self.semaphore = asyncio.Semaphore(MAX_PARALLEL_REQUESTS)

    def get_all_jobs(self) -> List[GEOmetadbUpdateJob]:
        """Retrieves all update job records."""
        try:
            with Session(self.engine) as session:
                stmt = select(GEOmetadbUpdateJob).order_by(GEOmetadbUpdateJob.date.desc())
                return list(session.scalars(stmt).all())
        except SQLAlchemyError as e:
            logger.exception(f"Failed to retrieve all jobs:")
            raise e

    def get_job_updates(self, job_id: int) -> List[GEOmetadbUpdateJobAssociation]:
        """Retrieves all GSE updates for a specific job."""
        try:
            with Session(self.engine) as session:
                stmt = select(GEOmetadbUpdateJobAssociation).where(
                    GEOmetadbUpdateJobAssociation.update_id == job_id
                ).order_by(GEOmetadbUpdateJobAssociation.gse_acc)
                return list(session.scalars(stmt).all())
        except SQLAlchemyError as e:
            logger.exception(f"Failed to retrieve updates for job {job_id}:")
            raise e

    def create_update_job(self, updated_gse_accessions: List[str], last_update_date_start: datetime.datetime,
                          last_update_date_end: datetime.datetime) -> GEOmetadbUpdateJob:
        """
        Creates a new update job record and links it to the updated GSE accessions.
        :param updated_gse_accessions: List of GEO accessions for the updated datasets.
        :param last_update_date_start: Earliest update date for the datasets that were downloaded.
        :param last_update_date_end: Latest update date for the datasets that were downloaded.
        """
        try:
            with Session(self.engine, expire_on_commit=False) as session:
                update_job = GEOmetadbUpdateJob(date=datetime.datetime.now(),
                                                last_update_date_start=last_update_date_start,
                                                last_update_date_end=last_update_date_end)
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

    def set_job_status(self, job_id: int, status: str) -> None:
        try:
            with Session(self.engine) as session:
                stmt = select(GEOmetadbUpdateJob).where(GEOmetadbUpdateJob.id == job_id)
                job = session.scalars(stmt).first()
                job.status = status
                session.commit()
        except SQLAlchemyError as e:
            logger.exception(f"Failed to mark job {job_id} as complete:")
            raise e

    async def set_gse_update_status_async(self, job_id: int, gse_accession: str, status: str) -> None:
        try:
            async with self.semaphore:
                async with AsyncSession(self.async_engine) as session:
                    stmt = select(GEOmetadbUpdateJobAssociation).where(
                        GEOmetadbUpdateJobAssociation.update_id == job_id,
                        GEOmetadbUpdateJobAssociation.gse_acc == gse_accession
                    )
                    job = (await session.scalars(stmt)).first()
                    job.status = status
                    await session.commit()
        except SQLAlchemyError as e:
            logger.exception(f"Failed to mark job {job_id} as complete:")
            raise e
