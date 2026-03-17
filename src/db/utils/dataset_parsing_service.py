import asyncio
import gzip
import logging
import os
import time
from asyncio import shield

import GEOparse
import pandas
from _asyncio import Future
from dacite import from_dict

from src.db.loaders.geoparse_to_geometadb import (
    format_geoparse_gse_metadata,
    format_geoparse_gsm_metadata,
)
from src.db.models import GSE, GSM
from src.db.utils.pipeline_models import DownloadedArchive, ParsedDataset

logger = logging.getLogger(__name__)


async def _periodic_flush(parser: GSEArchiveParser, interval: int) -> None:
    while True:
        await asyncio.sleep(interval)
        await parser.flush()

class GSEArchiveParser:
    """Service that parses downloaded GEO archives using a process pool."""

    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        executor,
        chunk_size: int,
        size_threshold_mb: int,
    ) -> None:
        self.loop = loop
        self.executor = executor
        self.chunk_size = chunk_size
        self.size_threshold_mb = size_threshold_mb
        self.queue: asyncio.Queue[tuple[DownloadedArchive, asyncio.Future[ParsedDataset]]] = asyncio.Queue()
        self.last_batch_time = time.time()
        self.lock = asyncio.Lock()
        self.batch = []
        self.flush_task = asyncio.create_task(_periodic_flush(self, 10))
        self._background_tasks = []
        self.last_flush_time = time.time()

    def stop_flushing_thread(self):
        self.flush_task.cancel()

    async def flush(self) -> None:
        """
        Parse a queued batch of small archives.

        :param force: If True, parse immediately even if batch is smaller than chunk size.
        """
        batch: list[tuple[DownloadedArchive, asyncio.Future[ParsedDataset]]] = []
        async with self.lock:
            time_since_last_flush = time.time() - self.last_flush_time
            if time_since_last_flush < 10:
                return
            batch = self.batch
            self.batch = []

        if not batch:
            return

        await self._parse_batch(batch)

    async def _parse_batch(self, batch: list[tuple[DownloadedArchive, Future[ParsedDataset]]]):
        async with self.lock:
            self.last_flush_time = time.time()

        archives = [item[0] for item in batch]
        archive_paths = [archive.archive_path for archive in archives]
        results = await self.loop.run_in_executor(
            self.executor,
            GSEArchiveParser.parse_dataset_batch,
            archive_paths,
        )
        for (archive, future), (gse, gsms) in zip(batch, results):
            future.set_result(
                ParsedDataset(
                    accession=archive.accession,
                    archive_path=archive.archive_path,
                    gse=gse,
                    gsms=gsms,
                )
            )

    async def parse_dataset(self, archive: DownloadedArchive) -> ParsedDataset:
        """
        Parse one downloaded archive into domain models.

        :param archive: Downloaded archive metadata.
        :return: Parsed dataset payload.
        """
        size_mb = os.path.getsize(archive.archive_path) / (1024 * 1024)
        if size_mb > self.size_threshold_mb:
            gse, gsms = await self.loop.run_in_executor(
                self.executor,
                GSEArchiveParser._parse_dataset,
                archive.archive_path,
            )
            return ParsedDataset(
                accession=archive.accession,
                archive_path=archive.archive_path,
                gse=gse,
                gsms=gsms,
            )

        future: asyncio.Future[ParsedDataset] = self.loop.create_future()
        async with self.lock:
            self.batch.append((archive, future))
            batch_to_parse = []
            if len(self.batch) >= self.chunk_size:
                batch_to_parse = self.batch
                self.batch = []

        if batch_to_parse:
            task = asyncio.create_task(self._parse_batch(batch_to_parse))
            self._background_tasks.append(task)
            task.add_done_callback(self._background_tasks.remove)

        return await shield(future)

    @staticmethod
    def _parse_dataset(gzip_path: str) -> tuple[GSE, list[GSM]]:
        """
        Parse one GEO dataset gzip file.

        :param gzip_path: Path to a GEO `.soft.gz` archive.
        :return: Parsed GSE and its GSM samples.
        """
        filesize = os.path.getsize(gzip_path) / 1024 / 1024
        try:
            start = time.time()
            geo = GEOparse.get_GEO(filepath=gzip_path, silent=True)
            duration = time.time() - start
            logger.info(
                "Parsed GEO dataset archive %s in %.2f seconds (%.2f MB)",
                gzip_path,
                duration,
                filesize,
            )
            gse = from_dict(GSE, format_geoparse_gse_metadata(geo.metadata))
            gsms = [from_dict(GSM, format_geoparse_gsm_metadata(gsm.metadata)) for gsm in geo.gsms.values()]
            if not geo.gsms:
                logger.warning("No samples found in dataset %s", gse.gse)
            return gse, gsms
        except gzip.BadGzipFile as exc:
            logger.exception("Invalid gzip file %s", gzip_path)
            raise exc
        except pandas.errors.ParserError as exc:
            logger.exception("Parser error for GEO archive %s", gzip_path)
            raise exc
        except Exception as exc:
            logger.exception("Unexpected error parsing GEO archive %s", gzip_path)
            raise exc

    @staticmethod
    def parse_dataset_batch(gzip_paths: list[str]) -> list[tuple[GSE, list[GSM]]]:
        """
        Parse multiple GEO dataset archives.

        :param gzip_paths: Archive paths.
        :return: Parsed results in input order.
        """
        return list(map(GSEArchiveParser._parse_dataset, gzip_paths))
