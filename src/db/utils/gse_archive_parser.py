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


async def _periodic_flush(parser: "GSEArchiveParser", interval: int) -> None:
    while True:
        await asyncio.sleep(interval)
        await parser.flush()


class GSEArchiveParser:
    """Service that parses downloaded GEO archives using a process pool."""

    def __init__(
            self,
            loop: asyncio.AbstractEventLoop,
            big_dataset_executor,
            small_dataset_executor,
            chunk_size: int,
            big_dataset_size_threshold_mb: int,
    ) -> None:
        self.loop = loop
        self.big_dataset_executor = big_dataset_executor
        self.small_dataset_executor = small_dataset_executor
        self.chunk_size = chunk_size
        self.big_dataset_size_threshold_mb = big_dataset_size_threshold_mb
        self.lock = asyncio.Lock()
        self.batch = []
        self.flush_task = None
        self._background_tasks = []
        self.last_flush_time = time.time()

    async def __aenter__(self) -> "GSEArchiveParser":
        self.flush_task = asyncio.create_task(_periodic_flush(self, 30))
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self.flush_task is not None:
            self.flush_task.cancel()
            try:
                await self.flush_task
            except asyncio.CancelledError:
                pass

        async with self.lock:
            batch = self.batch
            self.batch = []

        if batch:
            await self._process_archive_batch(batch)

        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)

    async def flush(self) -> None:
        """
        Parse a queued batch of small archives.
        """
        batch: list[tuple[DownloadedArchive, asyncio.Future[ParsedDataset]]] = []
        async with self.lock:
            time_since_last_flush = time.time() - self.last_flush_time
            if not(time_since_last_flush > 10 or len(self.batch) > self.chunk_size):
                return
            if len(self.batch) == 0:
                return
            batch = self.batch
            self.batch = []
            self.last_flush_time = time.time()

        task = asyncio.create_task(self._process_archive_batch(batch))
        self._background_tasks.append(task)
        task.add_done_callback(self._background_tasks.remove)

    async def _process_archive_batch(self, batch: list[tuple[DownloadedArchive, Future[ParsedDataset]]]):
        """
        Parses a batch of small archives and sets the results in their associated futures.
        """
        archives = [item[0] for item in batch]
        archive_paths = [archive.archive_path for archive in archives]
        results = await self.loop.run_in_executor(
            self.small_dataset_executor,
            GSEArchiveParser.parse_archives,
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

    async def submit_archive_for_parsing(self, archive: DownloadedArchive) -> ParsedDataset:
        """
        Submits an archive for parsing and returns the parsed dataset.

        This function determines whether the archive should be parsed with a specialized
        executor for large datasets or queued for batch processing, based on the size of
        the archive. For larger datasets exceeding the size threshold, the parsing is
        offloaded to a dedicated executor (big_dataset_executor). For smaller datasets, the archive is added
        to a batch of tasks that are processed when the batch size limit is reached.

        :param archive: The gzip archive to parse, containing GEO dataset metadata.
        :return: Parsed dataset containing information extracted from the archive.
        """
        size_mb = os.path.getsize(archive.archive_path) / (1024 * 1024)
        if size_mb > self.big_dataset_size_threshold_mb:
            gse, gsms = await self.loop.run_in_executor(
                self.big_dataset_executor,
                GSEArchiveParser._parse_archive,
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

        await self.flush()
        return await shield(future)

    @staticmethod
    def _parse_archive(gzip_path: str) -> tuple[GSE, list[GSM]]:
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
    def parse_archives(gzip_paths: list[str]) -> list[tuple[GSE, list[GSM]]]:
        """
        Parse multiple GEO dataset archives.

        :param gzip_paths: Archive paths.
        :return: Parsed results in input order.
        """
        return list(map(GSEArchiveParser._parse_archive, gzip_paths))
