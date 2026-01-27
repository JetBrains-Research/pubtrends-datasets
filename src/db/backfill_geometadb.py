import asyncio
import datetime
import gzip
import logging
import os.path
from concurrent.futures import ProcessPoolExecutor
from typing import List

import GEOparse
import aiofiles
import aiohttp
import pandas.errors
from dacite import from_dict
from tenacity import retry, stop_after_attempt
from tqdm.asyncio import tqdm_asyncio as tqdm

from src.config.config import Config
from src.db.geometadb_update_job_repository import GEOmetadbUpdateJobRepository
from src.db.geoparse_to_geometadb import format_geoparse_metadata
from src.db.get_geo_accessions_for_dates import get_gse_ids_by_last_update_date
from src.db.gse import GSE
from src.db.gse_repository import GSERepository
from src.helpers.is_gzip_vaild import is_gzip_valid
from src.helpers.remove_if_exists import async_remove_if_exists
from src.config.configure_log_file import configure_log_file

RETRY_ATTEMPTS = 3
GEO_FTP_HOST = "ftp.ncbi.nlm.nih.gov"
logger = logging.getLogger(__name__)


async def tqdm_gather(*fs, return_exceptions=False, **kwargs):
    if not return_exceptions:
        return await tqdm.gather(*fs, **kwargs)

    async def wrap(f):
        try:
            return await f
        except Exception as e:
            return e

    return await tqdm.gather(*map(wrap, fs), **kwargs)


class GEOmetadbBackfiller:
    def __init__(self, config: Config, gse_repository: GSERepository,
                 geometadb_update_job_repository: GEOmetadbUpdateJobRepository):
        self.dataset_parser_workers = config.dataset_parser_workers
        self.max_connections = config.max_ncbi_connections
        self.download_folder = config.dataset_download_folder
        self.gse_repository = gse_repository
        self.semaphore = asyncio.Semaphore(self.max_connections)
        self.show_progress = config.show_backfill_progress
        self.geometadb_update_job_repository = geometadb_update_job_repository

    @staticmethod
    def get_download_url(gse_accession: str) -> str:
        """
        Returns the download URL for a given GSE accession.

        :param gse_accession: GEO accession for the dataset (ex. GSE12345)
        :return: Download URL
        """
        return (
            f"https://{GEO_FTP_HOST}/"
            f"geo/series/{gse_accession[:-3]}nnn/{gse_accession}/soft/"
            f"{gse_accession}_family.soft.gz"
        )

    async def download_dataset(self, gse_accession: str, executor: ProcessPoolExecutor, session: aiohttp.ClientSession,
                               skip_existing: bool) -> GSE:
        """
        Downloads a GEO dataset archive, parses it using GEOparse, and saves it
        to the geometadb database.

        :param gse_accession: GEO accession number for the dataset (ex. GSE12345)
        :param executor: ProcessPoolExecutor to use for parsing.
        :param session: aiohttp ClientSession to use for downloading.
        :param skip_existing: If the dataset already exists in the database, return it instead of downloading it again.
        :return: GSE object representing the dataset.
        """
        existing_dataset = await self.gse_repository.get_gses_async([gse_accession])
        if existing_dataset and skip_existing:
            return existing_dataset[0]

        download_path = os.path.join(self.download_folder, f"{gse_accession}.soft.gz")
        url = GEOmetadbBackfiller.get_download_url(gse_accession)
        await self.download_gse_file(download_path, session, url)

        loop = asyncio.get_running_loop()
        gse = await loop.run_in_executor(executor, GEOmetadbBackfiller.parse_dataset, download_path)
        await self.gse_repository.save_gses_async([gse])
        logger.info(f"Saved dataset {gse_accession}")
        return gse

    @retry(stop=stop_after_attempt(RETRY_ATTEMPTS), reraise=True)
    async def download_gse_file(self, download_path: str, session: aiohttp.ClientSession, url: str):
        """
        Downloads the GEO dataset archive from the given URL and saves it to the given path.

        :param download_path: Path to save the downloaded file.
        :param session: aiohttp ClientSession to use for the download.
        :param url: URL to download the dataset archive from.
        """
        async with self.semaphore:
            try:
                logger.info(f"Downloading: {url}")
                async with (
                    session.get(url) as response,
                    aiofiles.open(download_path, mode='wb') as dataset_archive
                ):
                    async for chunk in response.content.iter_chunked(1024 * 1024):
                        await dataset_archive.write(chunk)
                if not await is_gzip_valid(download_path):
                    raise gzip.BadGzipFile("Downloaded file is not a valid gzip file")
                logger.info(f"Finished downloading: {url}")
            except (aiohttp.ClientResponseError, aiohttp.ClientConnectionError, asyncio.TimeoutError) as e:
                logger.exception(f"Network error downloading {url}: {e}")
                await async_remove_if_exists(download_path)
                raise e
            except Exception as e:
                logger.exception(f"Unexpected error saving {url} to {download_path}: {e}")
                await async_remove_if_exists(download_path)
                raise e

    @staticmethod
    def parse_dataset(gzip_path: str) -> GSE:
        """
        Parses a GEO dataset archive and returns a GSE object.

        :param gzip_path: Path to the gzip archive of the dataset.
        :return: GEOparse GSE object.
        """
        try:
            geo = GEOparse.get_GEO(filepath=gzip_path, silent=True)
            gse = from_dict(GSE, format_geoparse_metadata(geo.metadata))
            return gse
        except gzip.BadGzipFile as e:
            logger.exception(f"Error parsing GEO dataset archive - Invalid gzip file {gzip_path}")
            raise e
        except pandas.errors.ParserError as e:
            logger.exception(f"Error parsing GEO dataset archive {gzip_path}")
            raise e
        except Exception as e:
            logger.exception(f"Unexpected error parsing GEO dataset archive {gzip_path}")
            raise e

    def backfill_geometadb(self, start_date: datetime.datetime, end_date: datetime.datetime, skip_existing=True,
                           ignore_failures=False):
        """
        Downloads GEO datasets from the given date range and saves them to the
        geometadb database.

        :param start_date: Start date for the date range to download datasets from.
        :param end_date: End date for the date range to download datasets from.
        :param skip_existing: If True, datasets that already exist in the database will not be re-downloaded.
        :param ignore_failures: If True, datasets that fail to download will be ignored.
        :return: List of downloaded GEO datasets from the given timeframe.
        """
        gse_accessions = get_gse_ids_by_last_update_date(start_date, end_date)
        job = self.geometadb_update_job_repository.create_update_job(gse_accessions, start_date, end_date)

        async def set_gse_update_status(gse_acc: str, success: bool, error: Exception = None):
            status = "successful" if success else "failed"
            await self.geometadb_update_job_repository.set_gse_update_status_async(job.id, gse_acc, status)

        try:
            backfilled_gses = asyncio.run(self.download_datasets(gse_accessions, skip_existing, ignore_failures,
                                                                 on_dataset_complete=set_gse_update_status), debug=True)
            self.geometadb_update_job_repository.set_job_status(job.id, "successful")
            return backfilled_gses
        except KeyboardInterrupt as e:
            self.geometadb_update_job_repository.set_job_status(job.id, "cancelled")
            raise e
        except Exception as e:
            self.geometadb_update_job_repository.set_job_status(job.id, "failed")
            raise e

    async def download_datasets(self, gse_accessions: List[str], skip_existing=True, ignore_failures=False,
                                on_dataset_complete=None):
        """
        Downloads GEO datasets asynchronously and adds them to the geometadb database.

        :param gse_accessions: List of GEO accession numbers for the datasets to download (ex. GSE12345).
        :param skip_existing: If True, datasets that already exist in the database will not be re-downloaded.
        :param ignore_failures: If True, datasets that fail to download will be ignored.
        :param on_dataset_complete: Optional callback function(gse_accession, success, error) called after each dataset.
        :return: List of successfully downloaded GEO datasets.
        """
        pool_size = self.dataset_parser_workers

        logger.info(f"Downloading {len(gse_accessions)} datasets using {pool_size} workers")
        with ProcessPoolExecutor(pool_size, initializer=configure_log_file) as executor:
            async with aiohttp.ClientSession(raise_for_status=True,
                                             timeout=aiohttp.ClientTimeout(total=None, sock_connect=10,
                                                                           sock_read=10)) as session:
                tasks = [
                    self._download_dataset_with_callback(acc, executor, session, skip_existing, on_dataset_complete) for
                    acc in
                    gse_accessions]
                datasets = await tqdm_gather(*tasks,
                                             return_exceptions=ignore_failures) if self.show_progress else await asyncio.gather(
                    *tasks, return_exceptions=ignore_failures)
        if not ignore_failures:
            return datasets

        for gse in datasets:
            if isinstance(gse, Exception):
                logger.error(f"Failed to download dataset: {gse}")
        return [gse for gse in datasets if not isinstance(gse, Exception)]

    async def _download_dataset_with_callback(self, gse_accession, executor, session, skip_existing, callback):
        try:
            result = await self.download_dataset(gse_accession, executor, session, skip_existing)
            if callback:
                await callback(gse_accession, success=True, error=None)
            return result
        except Exception as e:
            if callback:
                await callback(gse_accession, success=False, error=e)
            raise e


if __name__ == '__main__':
    import argparse

    configure_log_file()

    parser = argparse.ArgumentParser(
        prog="GEOmetadb backfiller",
    description="Downloads GEO datasets that were last updated in the given date range and saves them to the geometadb database."
    )
    parser.add_argument(
        'start_date',
        type=lambda s: datetime.datetime.strptime(s, '%Y-%m-%d'),
        help='Start date for the date range to download datasets from (inclusive).'
    )
    parser.add_argument(
        'end_date',
        type=lambda s: datetime.datetime.strptime(s, '%Y-%m-%d'),
        default=datetime.datetime.now(),
        help='End date for the date range to download datasets from (inclusive). Defaults to today.',
        nargs='?'
    )
    parser.add_argument('--skip-existing', action='store_true',
                        help='If True, datasets that already exist in the database will not be re-downloaded.')
    parser.add_argument('--ignore-failures', action='store_true',
                        help='If True, datasets that fail to download will be ignored.')
    args = parser.parse_args()

    config = Config(test=False)
    gse_repository = GSERepository(config.geometadb_path)
    geometadb_update_job_repository = GEOmetadbUpdateJobRepository(config.geometadb_path)
    backfiller = GEOmetadbBackfiller(config, gse_repository, geometadb_update_job_repository)
    backfiller.backfill_geometadb(args.start_date, args.end_date, args.skip_existing, args.ignore_failures)
    print("Done")
