import asyncio
import datetime
import gzip
import unittest
from unittest.mock import Mock, AsyncMock, patch

import pandas.errors
from parameterized import parameterized

from src.config.config import Config
from src.db.models import GSE
from src.db.utils.backfill_geometadb import GEOmetadbBackfiller


class TestGEOmetadbBackfiller(unittest.TestCase):
    def setUp(self):
        self.test_config = Config(test=True)
        self.gse_repository = Mock()
        self.gse_repository.save_gses = Mock()
        self.gse_repository.get_gses = Mock(return_value=[])

        self.gsm_repository = Mock()
        self.gsm_repository.save_gsms = Mock()

        self.gse_accessions = ["GSE000000"]
        self.mock_get_accessions = self.enterContext(
            patch("src.db.utils.backfill_geometadb.get_gse_ids_by_last_update_date"))
        self.mock_get_accessions.return_value = self.gse_accessions

        self.backfiller = GEOmetadbBackfiller(self.test_config, self.gse_repository, self.gsm_repository)
        self.start_date = datetime.datetime(2025, 1, 1)
        self.end_date = datetime.datetime(2025, 1, 2)

        self.mock_downloader = self.enterContext(patch("src.db.utils.backfill_geometadb.GSEArchiveDownloader"))
        self.mock_parser = self.enterContext(patch("src.db.utils.backfill_geometadb.GSEArchiveParser"))
        self.mock_writer = self.enterContext(patch("src.db.utils.backfill_geometadb.DatasetWritingService"))

    def _create_mock_gse(self, accession: str) -> GSE:
        """Create a mock GSE object."""
        return GSE(
            gse=accession,
            title="Test Title",
            pubmed_id=12345,
        )

    def test_backfill_geometadb_success(self):
        # Setup mocks for the pipeline
        mock_downloaded_archive = Mock()
        mock_downloaded_archive.accession = self.gse_accessions[0]
        mock_downloaded_archive.archive_path = "/tmp/test.gz"

        gse = self._create_mock_gse(self.gse_accessions[0])
        mock_parsed_dataset = Mock()
        mock_parsed_dataset.accession = self.gse_accessions[0]
        mock_parsed_dataset.gse = gse
        mock_parsed_dataset.gsms = []

        self.mock_downloader.return_value.download_gse_archive = AsyncMock(return_value=mock_downloaded_archive)
        self.mock_parser.return_value.submit_archive_for_parsing = AsyncMock(return_value=mock_parsed_dataset)
        self.mock_writer.return_value.add = AsyncMock(return_value=mock_parsed_dataset)

        datasets = self.backfiller.backfill_geometadb(self.start_date, self.end_date)

        self.mock_get_accessions.assert_called_once()
        self.assertEqual(len(datasets), 1)
        self.assertEqual(datasets[0].gse, self.gse_accessions[0])

    def test_backfill_geometadb_download_failure(self):
        self.mock_downloader.return_value.download_gse_archive = AsyncMock(
            side_effect=asyncio.TimeoutError("Download failed")
        )

        self.assertRaises(asyncio.TimeoutError, self.backfiller.backfill_geometadb, self.start_date, self.end_date)
        self.mock_get_accessions.assert_called_once()
        self.mock_parser.parse_dataset.assert_not_called()
        self.mock_writer.add.assert_not_called()

    def test_backfill_geometadb_invalid_gzip(self):
        self.mock_downloader.return_value.download_gse_archive = AsyncMock(
            side_effect=gzip.BadGzipFile("Invalid gzip")
        )

        self.assertRaises(gzip.BadGzipFile, self.backfiller.backfill_geometadb, self.start_date, self.end_date)
        self.mock_get_accessions.assert_called_once()
        self.mock_parser.parse_dataset.assert_not_called()

    @parameterized.expand([
        (ValueError("Invalid GEO dataset"),),
        (gzip.BadGzipFile("Invalid gzip"),),
        (pandas.errors.ParserError("Invalid GPL table"),),
    ])
    def test_backfill_geometadb_parse_failure(self, throwable: Exception):
        mock_downloaded_archive = Mock()
        mock_downloaded_archive.accession = self.gse_accessions[0]
        mock_downloaded_archive.archive_path = "/tmp/test.gz"

        self.mock_downloader.return_value.download_gse_archive = AsyncMock(return_value=mock_downloaded_archive)
        self.mock_parser.return_value.submit_archive_for_parsing = AsyncMock(side_effect=throwable)

        self.assertRaises(type(throwable), self.backfiller.backfill_geometadb, self.start_date, self.end_date)
        self.mock_get_accessions.assert_called_once()
        self.mock_downloader.return_value.download_gse_archive.assert_called_once()
        self.mock_parser.return_value.submit_archive_for_parsing.assert_called_once()
        self.mock_writer.return_value.add.assert_not_called()

    def test_backfill_geometadb_invalid_date_range(self):
        self.assertRaises(ValueError, self.backfiller.backfill_geometadb, self.end_date, self.start_date)

    def test_backfill_geometadb_skip_existing(self):
        existing_gse = self._create_mock_gse(self.gse_accessions[0])
        self.gse_repository.get_gses.return_value = [existing_gse]

        datasets = self.backfiller.backfill_geometadb(self.start_date, self.end_date, skip_existing=True)

        self.mock_get_accessions.assert_called_once()
        # Should not download since it already exists
        self.mock_downloader.return_value.download_gse_archive.assert_not_called()
        self.assertEqual(len(datasets), 0)

    def test_backfill_geometadb_ignore_failures(self):
        self.mock_get_accessions.return_value = ["GSE000000", "GSE000001"]

        mock_downloaded_archive_1 = Mock()
        mock_downloaded_archive_1.accession = "GSE000000"
        mock_downloaded_archive_1.archive_path = "/tmp/test1.gz"

        mock_downloaded_archive_2 = Mock()
        mock_downloaded_archive_2.accession = "GSE000001"
        mock_downloaded_archive_2.archive_path = "/tmp/test2.gz"

        gse = self._create_mock_gse("GSE000001")
        mock_parsed_dataset = Mock()
        mock_parsed_dataset.accession = "GSE000001"
        mock_parsed_dataset.gse = gse
        mock_parsed_dataset.gsms = []

        async def download_side_effect(accession):
            if accession == "GSE000000":
                return mock_downloaded_archive_1
            return mock_downloaded_archive_2

        self.mock_downloader.return_value.download_gse_archive = AsyncMock(side_effect=download_side_effect)

        async def parse_side_effect(archive):
            if archive.accession == "GSE000000":
                raise ValueError("Parse error")
            return mock_parsed_dataset

        self.mock_parser.return_value.submit_archive_for_parsing = AsyncMock(side_effect=parse_side_effect)
        self.mock_writer.return_value.add = AsyncMock(return_value=mock_parsed_dataset)

        datasets = self.backfiller.backfill_geometadb(
            self.start_date, self.end_date, ignore_failures=True
        )

        self.mock_get_accessions.assert_called_once()
        self.assertEqual(len(datasets), 2)
        self.assertIsInstance(datasets[0], ValueError)
        self.assertEqual(datasets[1].gse, "GSE000001")
        self.assertEqual(self.mock_downloader.return_value.download_gse_archive.call_count, 2)
        self.assertEqual(self.mock_parser.return_value.submit_archive_for_parsing.call_count, 2)
        self.mock_writer.return_value.add.assert_called_once()
