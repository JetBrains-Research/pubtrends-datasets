import asyncio
import logging
import os
import sqlite3
from typing import List

from sqlalchemy import event
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, selectinload

from src.db.loaders.gse_loader import GSELoader
from src.db.models.gse import GSE
from src.db.repositories.sqlalchemy_engine_helpers import create_sync_engine

logger = logging.getLogger(__name__)
MAX_PARALLEL_REQUESTS = 10


class GSERepository(GSELoader):
    def __init__(self, geometadb_path: str) -> None:
        if not os.path.isfile(geometadb_path):
            raise RuntimeError(f"Geometadb file {geometadb_path} does not exist")
        if not os.access(geometadb_path, os.W_OK):
            raise RuntimeError(f"Geometadb file {geometadb_path} is not writable")
        self.engine = create_sync_engine(geometadb_path)
        self.async_engine = create_sync_engine(geometadb_path)
        self.geometadb_path = geometadb_path
        self.semaphore = asyncio.Semaphore(MAX_PARALLEL_REQUESTS)

        @event.listens_for(self.engine, "connect")
        def set_sqlite_text_factory(dbapi_connection, connection_record):
            dbapi_connection.text_factory = lambda x: x.decode(errors="replace")

    def save_gses(self, gses: List[GSE]) -> None:
        """
        Saves GEO datasets to the geometadb sqlite database.

        :param gses: List of GEO datasets to save.
        """
        if not gses:
            return
        try:
            with Session(self.engine) as session:
                for gse in gses:
                    session.merge(gse)
                session.commit()
        except SQLAlchemyError:
            logger.exception("Failed to save GEO datasets to geometadb:")
            raise

    @staticmethod
    async def executemany_with_retry(cursor, query, args):
        for _ in range(3):
            try:
                await cursor.executemany(query, args)
                return
            except sqlite3.OperationalError:
                pass
        await cursor.executemany(query, args)

    def get_gses(self, gse_accessions: List[str]) -> List[GSE]:
        """
        Loads GEO datasets from the geometadb sqlite database.

        :param gse_accessions: List of GEO accessions for the datasets.
        :return: List of GEO datasets
        """
        if not gse_accessions:
            return []
        try:
            with Session(self.engine) as session:
                statement = (
                    select(GSE)
                    .where(GSE.gse.in_(gse_accessions))
                    .options(
                        selectinload(GSE.gse_gsm_links)
                    )
                )
                return list(session.scalars(statement).all())
        except SQLAlchemyError as e:
            logger.exception("Failed to load GEO datasets from geometadb:")
            raise e

    async def get_gses_async(self, gse_accessions: List[str]) -> List[GSE]:
        """
        Loads GEO datasets from the geometadb sqlite database.

        :param gse_accessions: List of GEO accessions for the datasets.
        :return: List of GEO datasets
        """
        if not gse_accessions:
            return []
        try:
            async with self.semaphore:
                async with AsyncSession(self.async_engine) as session:
                    statement = (
                        select(GSE)
                        .where(GSE.gse.in_(gse_accessions))
                    )
                    return list((await session.scalars(statement)).all())
        except SQLAlchemyError:
            logger.exception("Failed to load GEO datasets from geometadb:")
            return []
