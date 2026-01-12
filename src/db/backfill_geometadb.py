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
from dacite import from_dict
from tenacity import retry, stop_after_attempt

from src.config.config import Config
from src.db.geoparse_to_geometadb import format_geoparse_metadata
from src.db.get_geo_accessions_for_dates import get_geo_ids
from src.db.gse import GSE
from src.db.gse_repository import GSERepository
from src.helpers.is_gzip_vaild import is_gzip_valid
from src.helpers.remove_if_exists import remove_if_exists

GEO_FTP_HOST = "ftp.ncbi.nlm.nih.gov"
logger = logging.getLogger(__name__)


class GEOmetadbBackfiller():
    def __init__(self, config: Config, gse_repository: GSERepository):
        self.dataset_parser_workers = config.dataset_parser_workers
        self.max_connections = config.max_ncbi_connections
        self.download_folder = config.dataset_download_folder
        self.repository = gse_repository
        self.semaphore = asyncio.Semaphore(self.max_connections)

    @staticmethod
    def get_ftp_path(gse_accession: str) -> str:
        """
        Returns FTP path for a given GSE accession.

        :param gse_accession: GEO accession for the dataset (ex. GSE12345)
        :return: FTP download link
        """
        return (
            f"geo/series/{gse_accession[:-3]}nnn/{gse_accession}/soft/"
            f"{gse_accession}_family.soft.gz"
        )

    async def download_dataset(self, gse_accession: str, executor: ProcessPoolExecutor, session: aiohttp.ClientSession) -> GSE:
        """
        Downloads a GEO dataset archive, parses it using GEOparse, and saves it
        to the geometadb database.

        :param gse_accession: GEO accession number for the dataset (ex. GSE12345)
        :param executor: ProcessPoolExecutor to use for parsing.
        :param session: aiohttp ClientSession to use for downloading.
        :return: GSE object representing the dataset.
        """
        download_path = os.path.join(self.download_folder, f"{gse_accession}.soft.gz")
        ftp_path = GEOmetadbBackfiller.get_ftp_path(gse_accession)
        url = f"https://{GEO_FTP_HOST}/{ftp_path}"
        await self.download_gse_file(download_path, session, url)

        loop = asyncio.get_running_loop()
        gse = await loop.run_in_executor(executor, GEOmetadbBackfiller.parse_dataset, download_path)
        await self.repository.save_gses_async([gse])
        logger.info(f"Downloaded and saved dataset {gse_accession}")
        return gse

    @retry(stop=stop_after_attempt(3))
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
                async with session.get(url) as response:
                    async with aiofiles.open(download_path, mode='wb') as dataset_archive:
                        await dataset_archive.write(await response.read())
                    if not await is_gzip_valid(download_path):
                        raise gzip.BadGzipFile("Downloaded file is not a valid gzip file")
            except (aiohttp.ClientResponseError, aiohttp.ClientConnectionError, asyncio.TimeoutError) as e:
                logger.exception(f"Network error downloading {url}: {e}")
                remove_if_exists(download_path)
                raise e
            except Exception as e:
                logger.exception(f"Unexpected error saving {url} to {download_path}: {e}")
                remove_if_exists(download_path)
                raise e


    @staticmethod
    @retry(stop=stop_after_attempt(3))
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
        except Exception as e:
            logger.exception(f"Error parsing GEO dataset archive {gzip_path}")
            raise e

    def backfill_geometadb(self, start_date: datetime.datetime, end_date: datetime.datetime):
        """
        Downloads GEO datasets from the given date range and saves them to the
        geometadb database.

        :param start_date: Start date for the date range to download datasets from.
        :param end_date: End date for the date range to download datasets from.
        :return: List of downloaded GEO datasets from the given timeframe.
        """
        gse_accessions = get_geo_ids(start_date, end_date)
        return asyncio.run(self.download_datasets(gse_accessions), debug=True)

    async def download_datasets(self, gse_accessions: List[str], ignore_failures=False):
        """
        Downloads GEO datasets asynchronously and adds them to the geometadb database.

        :param gse_accessions: List of GEO accession numbers for the datasets to download (ex. GSE12345).
        :param ignore_failures: If True, datasets that fail to download will be ignored.
        :return: List of successfully downloaded GEO datasets.
        """
        pool_size = self.dataset_parser_workers
        batch_size = 500
        all_results = []

        with ProcessPoolExecutor(pool_size) as executor:
            async with aiohttp.ClientSession(raise_for_status=True) as session:
                for i in range(0, len(gse_accessions), batch_size):
                    batch = gse_accessions[i:i + batch_size]
                    tasks = [self.download_dataset(acc, executor, session) for acc in batch]
                    results = await asyncio.gather(*tasks, return_exceptions=ignore_failures)
                    all_results.extend([gse for gse in results if not isinstance(gse, Exception)])
                    logger.info(f"Processed batch {i // batch_size + 1}")
        
        return all_results

if __name__ == '__main__':
    import logging
    import argparse

    parser = argparse.ArgumentParser()
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
    args = parser.parse_args()

    config = Config(test=False)
    repository = GSERepository(config.geometadb_path)
    backfiller = GEOmetadbBackfiller(config, repository)
    backfiller.backfill_geometadb(args.start_date, args.end_date)
    print("Done")
