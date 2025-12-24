import asyncio
import datetime
import os.path
from concurrent.futures import ProcessPoolExecutor
from time import time
from typing import List

import GEOparse
import aiofiles
import aiohttp
import aiosqlite
from dacite import from_dict

from src.config.config import Config
from src.db.geoparse_to_geometadb import format_geoparse_metadata
from src.db.get_geo_acessions_for_dates import get_geo_ids
from src.db.gse import GSE
from src.db.gse_repository import GSERepository

GEO_FTP_HOST = "ftp.ncbi.nlm.nih.gov"


class GEOmetadbBackfiller():
    def __init__(self, config: Config, repository: GSERepository):
        self.dataset_parser_workers = config.dataset_parser_workers
        self.max_connections = config.max_ncbi_connections
        self.download_folder = config.dataset_download_folder
        self.repository = repository

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

    async def download_dataset(self, gse_accession, executor, session, semaphore):
        download_path = os.path.join(self.download_folder, f"{gse_accession}.soft.gz")
        ftp_path = GEOmetadbBackfiller.get_ftp_path(gse_accession)
        url = f"https://{GEO_FTP_HOST}/{ftp_path}"
        print(f'fetch_data {gse_accession} started at {time()}')
        # Simulate an API request
        await self.download_gse_file(download_path, semaphore, session, url)

        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(executor, GEOmetadbBackfiller.process_data, download_path)
        print(f'fetch_data {gse_accession} returning results at time {time()}')
        if result is not None:
            await self.write_to_db(result)
        return result

    async def write_to_db(self, geo):
        gse = from_dict(GSE, format_geoparse_metadata(geo.metadata))
        await self.repository.save_gses_async([gse])


    async def download_gse_file(self, download_path: str, semaphore, session, url: str):
        async with semaphore:
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        dataset_archive = await aiofiles.open(download_path, mode='wb')
                        await dataset_archive.write(await response.read())
                        await dataset_archive.close()
                        print(f"Successfully downloaded: {download_path}")
                    else:
                        print(f"Failed to download {url}: Status {response.status}")
            except Exception as e:
                print(f"Error downloading {url}: {e}")

    @staticmethod
    def process_data(file):
        # Simulate CPU-bound data processing
        try:
            geo = GEOparse.get_GEO(filepath=file)
            print("Loaded", file)
            return geo
        except Exception:
            print("Error", file)
            return None

    def backfill_geometadb(self, start_date: datetime.datetime, end_date: datetime.datetime):
        gse_accessions = get_geo_ids(start_date, end_date)
        asyncio.run(self.download_datasets(gse_accessions))

    async def download_datasets(self, gse_accessions: List[str]):
        # Don't create a pool size larger than what we need
        # nor larger than the number of cores we have:
        semaphore = asyncio.Semaphore(self.max_connections)
        pool_size = self.dataset_parser_workers
        # Create the multiprocessing pool:
        with ProcessPoolExecutor(pool_size) as executor:
            # Fetch and process data
            async with aiohttp.ClientSession() as session:
                results = await asyncio.gather(
                    *(self.download_dataset(gse_accession, executor, session, semaphore) for gse_accession in gse_accessions))
            print(results)


# So this can runder Windows, MacOS, Linux, etc:
if __name__ == '__main__':  # Required for Windows
    import logging

    # Get a logger instance (using __name__ is a common practice)
    logger = logging.getLogger("GEOparse")

    # Set the specific logger's level to INFO
    logger.setLevel(logging.INFO)
    config = Config(test=False)
    print(config.geometadb_path)
    repository = GSERepository(config.geometadb_path)
    backfiller = GEOmetadbBackfiller(config, repository)
    #backfiller.backfill_geometadb(datetime.datetime(2025, 10, 1), datetime.datetime(2025, 10, 3))
    with open("subfolders.txt", "r") as f:
        gse_accessions = f.read().splitlines()
        asyncio.run(backfiller.download_datasets(gse_accessions))
