import asyncio
import json
import logging
import os
import sqlite3
from dataclasses import fields, astuple
from typing import List

import aiosqlite
from dacite import from_dict

from src.db.gse import GSE

logger = logging.getLogger(__name__)
MAX_PARALLEL_REQUESTS = 10


class GSERepository:
    def __init__(self, geometadb_path: str) -> None:
        self.geometadb_path = geometadb_path
        if not os.path.isfile(self.geometadb_path):
            raise RuntimeError(f"Geometadb file {self.geometadb_path} does not exist")
        if not os.access(self.geometadb_path, os.W_OK):
            raise RuntimeError(f"Geometadb file {self.geometadb_path} is not writable")
        self.check_geometadb_integrity()
        self.semaphore = asyncio.Semaphore(MAX_PARALLEL_REQUESTS)

    def check_geometadb_integrity(self):
        """
        Checks if the geometadb sqlite database is corrupted.
        Raises a RuntimeError if the database is corrupted.
        """
        try:
            with sqlite3.connect(self.geometadb_path) as conn:
                pass
                #cursor = conn.cursor()
                #cursor.execute("PRAGMA integrity_check;")
                #result = cursor.fetchone()
                #if not result or result[0] != "ok":
                    #raise RuntimeError("Geometadb file is corrupted")
        except sqlite3.Error:
            raise RuntimeError("Geometadb file is corrupted")

    def save_gses(self, gses: List[GSE]) -> None:
        """
        Saves GEO datasets to the geometadb sqlite database.

        :param gses: List of GEO datasets to save.
        """
        if not gses:
            return

        try:
            with sqlite3.connect(self.geometadb_path) as conn:
                cursor = conn.cursor()
                gse_tuples = [astuple(gse) for gse in gses]
                cursor.executemany(self._create_insert_query(), gse_tuples)
                cursor.close()
        except sqlite3.Error:
            # Just log the exception so as not to fail the whole pipeline.
            logger.exception("Failed to save GEO datasets to geometadb:")

    @staticmethod
    def _create_insert_query() -> str:
        field_names = [f.name for f in fields(GSE)]
        headers = ','.join(field_names)
        placeholders = ','.join(['?'] * len(field_names))
        table = 'gse'
        return f"INSERT OR REPLACE INTO {table} ({headers}) VALUES ({placeholders})"

    async def save_gses_async(self, gses: List[GSE]) -> None:
        if not gses:
            return

        try:
            async with aiosqlite.connect(self.geometadb_path, timeout=10) as conn:
                cursor = await conn.cursor()
                gse_tuples = [astuple(gse) for gse in gses]
                await self.executemany_with_retry(cursor, self._create_insert_query(), gse_tuples)
                await conn.commit()
                await cursor.close()
        except sqlite3.Error as e:
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
            with sqlite3.connect(self.geometadb_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM gse WHERE gse IN (SELECT value FROM json_each(?))",
                               (json.dumps(gse_accessions),))
                results = cursor.fetchall()
                return [GSE(*result) for result in results]
        except sqlite3.Error:
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
                async with aiosqlite.connect(self.geometadb_path, timeout=10) as conn:
                    conn.row_factory = aiosqlite.Row
                    async with conn.execute(
                            "SELECT * FROM gse WHERE gse IN (SELECT value FROM json_each(?))",
                            (json.dumps(gse_accessions),)
                    ) as cursor:
                        rows = await cursor.fetchall()
                        return [from_dict(GSE, dict(row)) for row in rows]
        except sqlite3.Error:
            logger.exception("Failed to load GEO datasets from geometadb:")
            return []
