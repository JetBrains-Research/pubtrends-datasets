import asyncio
import gzip
import logging
import os

import aiofiles
import aiohttp
from tenacity import retry, stop_after_attempt

from src.config.config import Config
from src.db.utils.pipeline_models import DownloadedArchive
from src.helpers.is_gzip_vaild import is_gzip_valid
from src.helpers.remove_if_exists import async_remove_if_exists

RETRY_ATTEMPTS = 3
GEO_FTP_HOST = "ftp.ncbi.nlm.nih.gov"
logger = logging.getLogger(__name__)


class GSEArchiveDownloader:
    """Service that downloads GEO archives and validates gzip integrity."""

    def __init__(self, config: Config, session: aiohttp.ClientSession, dont_redownload: bool) -> None:
        self.download_folder = config.dataset_download_folder
        self.max_connections = config.max_ncbi_connections
        self.session = session
        self.dont_redownload = dont_redownload

    @retry(stop=stop_after_attempt(RETRY_ATTEMPTS), reraise=True)
    async def download_gzip(self, download_path: str, url: str) -> None:
        """
        Download a gzip archive from the given URL and save it to the given path.

        :param download_path: Path where the file will be saved.
        :param url: URL to download from.
        """
        try:
            logger.info("Downloading: %s", url)
            async with (
                self.session.get(url) as response,
                aiofiles.open(download_path, mode="wb") as dataset_archive,
            ):
                async for chunk in response.content.iter_chunked(1024 * 1024):
                    await dataset_archive.write(chunk)
            if not await is_gzip_valid(download_path):
                raise gzip.BadGzipFile("Downloaded file is not a valid gzip file")
            logger.info("Finished downloading: %s", url)
        except (aiohttp.ClientResponseError, aiohttp.ClientConnectionError, asyncio.TimeoutError) as exc:
            logger.exception("Network error downloading %s", url)
            await async_remove_if_exists(download_path)
            raise exc
        except Exception as exc:
            logger.exception("Unexpected error saving %s to %s", url, download_path)
            await async_remove_if_exists(download_path)
            raise exc

    async def download_gse_archive(self, gse_accession: str) -> DownloadedArchive:
        """
        Download a GEO Series (GSE) archive file.

        :param gse_accession: GSE accession code (for example, GSE12345).
        :return: Download metadata for the saved archive.
        """
        download_path = os.path.join(self.download_folder, f"{gse_accession}.soft.gz")
        url = GSEArchiveDownloader.get_download_url(gse_accession)
        if os.path.exists(download_path) and self.dont_redownload:
            return DownloadedArchive(accession=gse_accession, archive_path=download_path)
        await self.download_gzip(download_path, url)
        return DownloadedArchive(accession=gse_accession, archive_path=download_path)

    @staticmethod
    def get_download_url(gse_accession: str) -> str:
        """
        Build the GEO download URL for a given accession.

        :param gse_accession: GEO accession code.
        :return: Archive URL.
        """
        return (
            f"https://{GEO_FTP_HOST}/"
            f"/geo/series/{gse_accession[:-3]}nnn/{gse_accession}/soft/"
            f"{gse_accession}_family.soft.gz"
        )
