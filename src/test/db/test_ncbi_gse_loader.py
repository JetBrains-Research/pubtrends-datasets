import unittest
from typing import List
from unittest.mock import Mock, patch

import requests
from parameterized import parameterized

from src.config.config import Config
from src.db.gse import GSE
from src.db.ncbi_gse_loader import NCBIGSELoader
from src.exception.geo_error import GEOError


class TestNCBIGSELoader(unittest.TestCase):
    def setUp(self):
        self.mock_session = Mock()
        self.loader = NCBIGSELoader(self.mock_session, Config(test=True))

    @staticmethod
    def _make_ok_response(gse_accession: str):
        resp = Mock()
        resp.status_code = 200
        resp.iter_lines.return_value = iter([f"^SERIES = {gse_accession}", "!Series_title = Title",
                                             f"!Series_geo_accession = {gse_accession}", f"!Series_pubmed_id = 12345"])
        resp.raise_for_status.return_value = None
        return resp

    @staticmethod
    def _make_error_response():
        resp = Mock()
        resp.status_code = 500
        resp.iter_lines.return_value = iter(["ERROR"])
        http_error = requests.HTTPError()
        http_error.response = resp
        resp.raise_for_status.side_effect = http_error
        return resp

    @parameterized.expand([
        (["GSE116672"], ["GSE116672"]),
        ([], []),
        (["GSE100", "GSE200"], ["GSE100", "GSE200"]),
    ])
    @patch("src.db.ncbi_gse_loader.sqlite3.connect")
    def test_load_gses_success(self, gse_accessions: List[str], expected_ids: List[str], mock_sql):
        mock_conn = mock_sql.return_value.__enter__.return_value
        mock_cursor = mock_conn.cursor.return_value
        executemany_mock = mock_cursor.executemany
        executemany_mock.side_effect = None
        executemany_mock.return_value = None
        # Prepare responses for each accession
        self.mock_session.get.side_effect = [self._make_ok_response(accession) for accession in gse_accessions]

        gses: List[GSE] = self.loader.load_gses(gse_accessions)
        gse_ids = [g.gse for g in gses]
        self.assertListEqual(gse_ids, expected_ids)

        self.assertEqual(self.mock_session.get.call_count, len(gse_accessions))
        self.assertEqual(executemany_mock.call_count, 1)
        sql_args, kwargs = executemany_mock.call_args
        self.assertEqual(len(sql_args[1]), len(gse_accessions))

    def test_load_gses_http_error(self):
        err_response = self._make_error_response()

        self.mock_session.get.return_value = err_response

        with self.assertRaises(GEOError):
            self.loader.load_gses(["GSE12345"])

        self.mock_session.get.assert_called_once()

    def test_load_gses_connection_failure(self):
        req_exc = requests.RequestException()
        req_exc.response = Mock()
        req_exc.response.status_code = 408

        self.mock_session.get.side_effect = req_exc

        with self.assertRaises(GEOError):
            self.loader.load_gses(["GSE99999"])

        self.mock_session.get.assert_called_once()
