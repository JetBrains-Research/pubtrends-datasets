import datetime
import unittest
from unittest.mock import Mock, AsyncMock, patch
import gzip

from src.config.config import Config
from src.db.backfill_geometadb import GEOmetadbBackfiller

class TestGEOmetadbBackfiller(unittest.TestCase):
    def setUp(self):
        self.mock_session = Mock()
        self.test_config = Config(test=True)
        self.repository = Mock()
        self.repository.save_gses_async = AsyncMock()
        self.backfiller = GEOmetadbBackfiller(self.test_config, self.repository)

    @staticmethod
    def _make_response(gse_accession: str):
        raw_body = "\n".join([f"^SERIES = {gse_accession}", "!Series_title = Title",
                                  f"!Series_geo_accession = {gse_accession}", f"!Series_pubmed_id = 12345"])
        body = gzip.compress(raw_body.encode("utf-8"))
        mock_response = AsyncMock()
        mock_response.read.return_value = body
        mock_response.status = 200
        return mock_response

    @patch("src.db.backfill_geometadb.get_geo_ids")
    @patch("aiohttp.ClientSession.get")
    def test_backfill_geometadb_success(self, mock_get: Mock, mock_get_accessions: Mock):
        mock_get.return_value.__aenter__.return_value = self._make_response("GSE12345")
        mock_get_accessions.return_value = ["GSE12345"]
        start_date, end_date = datetime.datetime(2025, 1, 1), datetime.datetime(2025, 1, 2)
        datasets = self.backfiller.backfill_geometadb(start_date, end_date)
        mock_get_accessions.assert_called_once()
        mock_get.assert_called_once()
        self.assertEqual(len(datasets), 1)
        self.assertEqual(datasets[0].gse, "GSE12345")
        self.repository.save_gses_async.assert_called_once()

    def test_backfill_geometadb_download_failure(self):
        pass

    def test_backfill_geometadb_invalid_gzip(self):
        pass

    def test_backfill_geometadb_parse_failure(self):
        pass

    def test_backfill_geometadb_invalid_date_range(self):
        pass


