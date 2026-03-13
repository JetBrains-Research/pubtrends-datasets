import asyncio
import logging
import os
from typing import List

from sqlalchemy import create_engine, event, select
from sqlalchemy.event import listens_for
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import Session

from src.db.models import GSE_GSM
from src.db.models.gsm import GSM
from src.db.loaders.gsm_loader import GSMLoader
from src.db.repositories.gse_repository import MAX_PARALLEL_REQUESTS

logger = logging.getLogger(__name__)


class GSMRepository(GSMLoader):
    def __init__(self, geometadb_path: str) -> None:
        if not os.path.isfile(geometadb_path):
            raise RuntimeError(f"Geometadb file {geometadb_path} does not exist")
        if not os.access(geometadb_path, os.W_OK):
            raise RuntimeError(f"Geometadb file {geometadb_path} is not writable")
        self.engine = create_engine(f"sqlite:///{geometadb_path}")
        self.async_engine = create_async_engine(f"sqlite+aiosqlite:///{geometadb_path}", connect_args={"timeout": 15})
        self.geometadb_path = geometadb_path
        self.semaphore = asyncio.Semaphore(MAX_PARALLEL_REQUESTS)

        @event.listens_for(self.engine, "connect")
        def set_sqlite_text_factory(dbapi_connection, connection_record):
            dbapi_connection.text_factory = lambda x: x.decode(errors="replace")

        @listens_for(self.async_engine.sync_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()

    def save_gsms(self, gsms: List[GSM]) -> None:
        """
        Saves GEO samples to the geometadb sqlite database.

        :param gsms: List of GEO samples to save.
        """
        if not gsms:
            return
        gse_gsm_links = [GSE_GSM(gse=gsm.series_id, gsm=gsm.gsm) for gsm in gsms]
        try:
            with Session(self.engine) as session:
                session.add_all(gsms)
                session.add_all(gse_gsm_links)
                session.commit()
        except SQLAlchemyError:
            logger.exception("Failed to save GEO samples to geometadb:")
            raise

    def get_gsms(self, gsm_accessions: List[str]) -> List[GSM]:
        """
        Loads GEO samples from the geometadb sqlite database.

        :param gsm_accessions: List of GEO accessions for the samples.
        :return: List of GEO samples
        """
        if not gsm_accessions:
            return []
        try:
            with Session(self.engine) as session:
                statement = select(GSM).where(GSM.gsm.in_(gsm_accessions))
                return list(session.scalars(statement).all())
        except SQLAlchemyError as e:
            logger.exception("Failed to load GEO samples from geometadb:")
            raise e

    async def save_gsms_async(self, gsms: List[GSM]) -> None:
        """
        Saves GEO samples to the geometadb sqlite database asynchronously.

        :param gsms: List of GEO samples to save.
        """
        if not gsms:
            return
        gse_gsm_links = [GSE_GSM(gse=gsm.series_id, gsm=gsm.gsm) for gsm in gsms]
        try:
            async with AsyncSession(self.async_engine) as session:
                for gsm in gsms:
                    await session.merge(gsm)
                for gse_gsm_link in gse_gsm_links:
                    await session.merge(gse_gsm_link)
                await session.commit()
        except SQLAlchemyError:
            logger.exception("Failed to save GEO samples to geometadb:")
            raise
