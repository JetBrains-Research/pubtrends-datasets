import asyncio
import datetime
import logging
from concurrent.futures import ProcessPoolExecutor
from typing import List

import aiohttp

from src.config.config import Config
from src.config.configure_log_file import configure_log_file
from src.db.models import GSE
from src.db.utils.dataset_parsing_service import GSEArchiveParser
from src.db.utils.dataset_writing_service import DatasetWritingService
from src.db.utils.get_geo_accessions_for_dates import get_gse_ids_by_last_update_date
from src.db.utils.gse_archive_downloader import GSEArchiveDownloader
from tqdm.asyncio import tqdm_asyncio as tqdm

from src.db.repositories.gse_repository import GSERepository
from src.db.repositories.gsm_repository import GSMRepository

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
    """Coordinates download, parse, and save stages for GEO backfill."""

    def __init__(
            self,
            config: Config,
            gse_repository: GSERepository,
            gsm_repository: GSMRepository,
    ) -> None:
        self.config = config
        self.dataset_parser_workers = config.dataset_parser_workers
        self.gse_repository = gse_repository
        self.gsm_repository = gsm_repository
        self.show_progress = config.show_backfill_progress
        self.chunk_size = config.chunk_size
        self.big_gzip_threshold_mb = config.big_gzip_threshold_mb
        self.small_dataset_parser_workers = config.small_dataset_parser_workers
        self.big_dataset_parser_workers = config.big_dataset_parser_workers

    def backfill_geometadb(
            self,
            start_date: datetime.datetime,
            end_date: datetime.datetime,
            skip_existing: bool = True,
            ignore_failures: bool = False,
            dont_redownload: bool = False,
    ) -> list[GSE]:
        """
        Download and persist GEO datasets from the given date range.

        :param start_date: Inclusive start date.
        :param end_date: Inclusive end date.
        :param skip_existing: If True, skip datasets already in geometadb.
        :param ignore_failures: If True, continue after stage failures.
        :param dont_redownload: If True, does not re-download archives that have already been downloaded.
        :return: Successfully parsed and saved GSE objects.
        """
        if end_date < start_date:
            raise ValueError("End date must be after start date")

        gse_accessions = get_gse_ids_by_last_update_date(start_date, end_date)
        return asyncio.run(
            self.download_datasets(gse_accessions, skip_existing=skip_existing, ignore_failures=ignore_failures,
                                   dont_redownload=dont_redownload),
            debug=True,
        )

    async def _filter_existing_accessions(
            self,
            gse_accessions: list[str],
            skip_existing: bool,
    ) -> list[str]:
        """
        Filter out accessions already present in geometadb.

        :param gse_accessions: Candidate GEO accessions.
        :param skip_existing: If False, return input unchanged.
        :return: Accessions that should be downloaded.
        """
        if not skip_existing or not gse_accessions:
            return gse_accessions

        existing_gses = await asyncio.to_thread(self.gse_repository.get_gses, gse_accessions)
        existing_accessions = {gse.gse for gse in existing_gses if gse.gse is not None}
        filtered_accessions = [accession for accession in gse_accessions if accession not in existing_accessions]
        skipped_count = len(gse_accessions) - len(filtered_accessions)
        if skipped_count:
            logger.info("Skipping %d already existing datasets", skipped_count)
        return filtered_accessions

    async def download_datasets(
            self,
            gse_accessions: list[str],
            skip_existing: bool = True,
            ignore_failures: bool = False,
            dont_redownload: bool = False,
    ) -> List[GSE]:
        """
        Run the backfill pipeline as parallel per-accession tasks.

        :param gse_accessions: GEO accessions to process.
        :param skip_existing: If True, skip datasets already present.
        :param ignore_failures: If True, continue processing after stage failures.
        :return: Successfully parsed and saved GSE models.
        """
        accessions_to_process = await self._filter_existing_accessions(gse_accessions, skip_existing)
        if not accessions_to_process:
            return []

        logger.info(
            "Downloading %d datasets using %d parser workers",
            len(accessions_to_process),
            self.dataset_parser_workers,
        )

        with (ProcessPoolExecutor(self.big_dataset_parser_workers,
                                  initializer=configure_log_file) as big_dataset_executor,
              ProcessPoolExecutor(self.small_dataset_parser_workers,
                                  initializer=configure_log_file) as small_dataset_executor):
            async with aiohttp.ClientSession(
                    raise_for_status=True,
                    timeout=aiohttp.ClientTimeout(total=None, sock_connect=10, sock_read=10),
                    connector=aiohttp.TCPConnector(limit=self.config.max_ncbi_connections),
            ) as session:
                loop = asyncio.get_running_loop()
                downloader = GSEArchiveDownloader(self.config, session, dont_redownload)
                parser = GSEArchiveParser(loop, big_dataset_executor, small_dataset_executor, self.chunk_size,
                                          self.big_gzip_threshold_mb)
                writer = DatasetWritingService(
                    gse_repository=self.gse_repository,
                    gsm_repository=self.gsm_repository,
                )

                async def process_single_dataset(accession: str) -> GSE:
                    """Download, parse, and write a single dataset through the pipeline."""
                    try:
                        downloaded_archive = await downloader.download_gse_archive(accession)
                        parsed_dataset = await parser.submit_archive_for_parsing(downloaded_archive)
                        written_parsed_dataset = await writer.add(parsed_dataset)
                        return written_parsed_dataset.gse
                    except Exception:
                        logger.exception("Failed to process dataset %s", accession)
                        raise

                pipeline_tasks = [process_single_dataset(acc) for acc in accessions_to_process]
                if self.show_progress:
                    return await tqdm_gather(*pipeline_tasks, return_exceptions=ignore_failures)
                else:
                    return await asyncio.gather(*pipeline_tasks, return_exceptions=ignore_failures)


if __name__ == "__main__":
    import argparse

    configure_log_file()
    from src.db.repositories.gse_repository import GSERepository
    from src.db.repositories.gsm_repository import GSMRepository

    parser = argparse.ArgumentParser(
        prog="GEOmetadb backfiller",
        description="Downloads GEO datasets that were last updated in the given date range and saves them to the geometadb database.",
    )
    parser.add_argument(
        "start_date",
        type=lambda s: datetime.datetime.strptime(s, "%Y-%m-%d"),
        help="Start date for the date range to download datasets from (inclusive).",
    )
    parser.add_argument(
        "end_date",
        type=lambda s: datetime.datetime.strptime(s, "%Y-%m-%d"),
        default=datetime.datetime.now(),
        help="End date for the date range to download datasets from (inclusive). Defaults to today.",
        nargs="?",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="If True, datasets that already exist in the database will be skipped",
    )
    parser.add_argument(
        "--ignore-failures",
        action="store_true",
        help="If True, datasets that fail to download or parse will be ignored.",
    )
    parser.add_argument(
        "--dont-redownload",
        action="store_true",
        help="If True, archives that have already been downloaded will not be re-downloaded. However, they will be parsed and saved.",
    )
    args = parser.parse_args()
    logger.setLevel(logging.WARNING)

    config = Config(test=False)
    gse_repository = GSERepository(config.geometadb_path)
    gsm_repository = GSMRepository(config.geometadb_path)
    backfiller = GEOmetadbBackfiller(config, gse_repository, gsm_repository)
    backfiller.backfill_geometadb(args.start_date, args.end_date, args.skip_existing, args.ignore_failures,
                                  args.dont_redownload)
