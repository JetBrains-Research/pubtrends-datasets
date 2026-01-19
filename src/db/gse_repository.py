import asyncio
import logging
import os
import sqlite3
from typing import List

import sqlalchemy.exc
from sqlalchemy import create_engine
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import Session

from src.db.gse import GSE

logger = logging.getLogger(__name__)
MAX_PARALLEL_REQUESTS = 10


class GSERepository:
    def __init__(self, geometadb_path: str) -> None:
        if not os.path.isfile(geometadb_path):
            raise RuntimeError(f"Geometadb file {geometadb_path} does not exist")
        if not os.access(geometadb_path, os.W_OK):
            raise RuntimeError(f"Geometadb file {geometadb_path} is not writable")
        self.engine = create_engine(f"sqlite:///{geometadb_path}")
        self.async_engine = create_async_engine(f"sqlite+aiosqlite:///{geometadb_path}")
        self.geometadb_path = geometadb_path
        self.semaphore = asyncio.Semaphore(MAX_PARALLEL_REQUESTS)

    def save_gses(self, gses: List[GSE]) -> None:
        """
        Saves GEO datasets to the geometadb sqlite database.

        :param gses: List of GEO datasets to save.
        """
        if not gses:
            return
        try:
            with Session(self.engine) as session:
                session.add_all(gses)
                session.commit()
        except SQLAlchemyError:
            logger.exception("Failed to save GEO datasets to geometadb:")
            raise

    async def save_gses_async(self, gses: List[GSE]) -> None:
        if not gses:
            return

        try:
            async with AsyncSession(self.async_engine) as session:
                session.add_all(gses)
                await session.commit()
        except sqlalchemy.exc.SQLAlchemyError as e:
            # Just log the exception so as not to fail the whole pipeline.
            logger.exception("Failed to save GEO datasets to geometadb:")
            raise e

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
                )
                return list(session.scalars(statement).all())
        except SQLAlchemyError:
            logger.exception("Failed to load GEO datasets from geometadb:")
            return []

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
