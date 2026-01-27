import datetime
import unittest
from unittest.mock import Mock, AsyncMock, patch
import gzip
import asyncio

import pandas.errors
from parameterized import parameterized

from src.config.config import Config
from src.db.backfill_geometadb import GEOmetadbBackfiller, RETRY_ATTEMPTS
from src.test.helpers.async_iterator import AsyncIterator


class TestGEOmetadbBackfiller(unittest.TestCase):
    def setUp(self):
        self.test_config = Config(test=True)
        self.gse_repository = Mock()
        self.gse_repository.save_gses_async = AsyncMock()
        self.gse_repository.get_gses_async = AsyncMock(return_value=[])

        self.geometadb_update_job_repository = Mock()
        self.geometadb_update_job_repository.create_update_job.return_value = Mock()
        self.geometadb_update_job_repository.set_gse_update_status_async = AsyncMock()

        self.gse_accessions = ["GSE000000"]
        self.mock_get_accessions = self.enterContext(patch("src.db.backfill_geometadb.get_gse_ids_by_last_update_date"))
        self.mock_get_accessions.return_value = self.gse_accessions
        self.mock_aiohttp_get = self.enterContext(patch("aiohttp.ClientSession.get"))
        self.mock_get_running_loop = self.enterContext(patch("asyncio.get_running_loop"))
        self.mock_get_running_loop.return_value.run_in_executor = AsyncMock()
        self.mock_get_running_loop.return_value.run_in_executor.side_effect = lambda executor, func, *args: func(*args)

        self.backfiller = GEOmetadbBackfiller(self.test_config, self.gse_repository, self.geometadb_update_job_repository)
        self.start_date = datetime.datetime(2025, 1, 1)
        self.end_date = datetime.datetime(2025, 1, 2)

    def _assert_update_job_created(self):
        self.geometadb_update_job_repository.create_update_job.assert_called_once()
        self.assertEqual(self.geometadb_update_job_repository.create_update_job.call_args[0][0], self.gse_accessions)
        self.assertEqual(self.geometadb_update_job_repository.create_update_job.call_args[0][1], self.start_date)
        self.assertEqual(self.geometadb_update_job_repository.create_update_job.call_args[0][2], self.end_date)

    def _prepare_mock_geo_dataset_response(self, gse_accession: str, valid_body=True):
        body = None
        if valid_body:
            raw_body = "\n".join([f"^SERIES = {gse_accession}", "!Series_title = Title",
                                  f"!Series_geo_accession = {gse_accession}", f"!Series_pubmed_id = 12345"])
            body = gzip.compress(raw_body.encode("utf-8"))
        else:
            body = "^INVALID\n".encode("utf-8")
        mock_response = AsyncMock()
        mock_response.read.return_value = body
        mock_response.status = 200
        mock_response.content = Mock()
        mock_response.content.iter_chunked.side_effect = lambda chunk_size: AsyncIterator([body])
        self.mock_aiohttp_get.return_value.__aenter__.return_value = mock_response

    def test_backfill_geometadb_success(self):
        self._prepare_mock_geo_dataset_response(self.gse_accessions[0])

        datasets = self.backfiller.backfill_geometadb(self.start_date, self.end_date)

        self.mock_get_accessions.assert_called_once()
        self._assert_update_job_created()
        self.mock_aiohttp_get.assert_called_once()
        self.assertEqual(len(datasets), 1)
        self.assertEqual(datasets[0].gse, self.gse_accessions[0])
        self.gse_repository.save_gses_async.assert_called_once()

    def test_backfill_geometadb_download_failure(self):
        self.mock_aiohttp_get.side_effect = asyncio.TimeoutError("Download failed")

        self.assertRaises(asyncio.TimeoutError, self.backfiller.backfill_geometadb, self.start_date, self.end_date)
        self._assert_update_job_created()
        self.mock_get_accessions.assert_called_once()
        self.assertEqual(self.mock_aiohttp_get.call_count, RETRY_ATTEMPTS)

    def test_backfill_geometadb_invalid_gzip(self):
        self._prepare_mock_geo_dataset_response(self.gse_accessions[0], valid_body=False)

        self.assertRaises(gzip.BadGzipFile, self.backfiller.backfill_geometadb, self.start_date, self.end_date)
        self._assert_update_job_created()
        self.mock_get_accessions.assert_called_once()
        self.assertEqual(self.mock_aiohttp_get.call_count, RETRY_ATTEMPTS)

    @parameterized.expand([
        (ValueError("Invalid GEO dataset")),
        (gzip.BadGzipFile("Invalid gzip")),
        (pandas.errors.ParserError("Invalid GPL table")),
    ])
    @patch("GEOparse.get_GEO")
    def test_backfill_geometadb_parse_failure(self, throwable: Exception, mock_get_geo: Mock):
        self._prepare_mock_geo_dataset_response(self.gse_accessions[0])
        mock_get_geo.side_effect = throwable

        self.assertRaises(type(throwable), self.backfiller.backfill_geometadb, self.start_date, self.end_date)
        self.mock_get_accessions.assert_called_once()
        self.mock_aiohttp_get.assert_called_once()
        mock_get_geo.assert_called_once()
        self._assert_update_job_created()


    def test_backfill_geometadb_invalid_date_range(self):
        pass
