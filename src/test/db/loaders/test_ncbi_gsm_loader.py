import unittest
from typing import List
from unittest.mock import Mock

import requests
from parameterized import parameterized

from src.config.config import Config
from src.db.loaders.ncbi_gsm_loader import NCBIGSMLoader
from src.db.models.gsm import GSM
from src.exception.geo_error import GEOError
from src.test.helpers.http import create_mock_response


class TestNCBIGSMLoader(unittest.TestCase):
    def setUp(self):
        self.mock_session = Mock()
        self.test_config = Config(test=True)
        self.repository = Mock()
        self.loader = NCBIGSMLoader(self.mock_session, self.repository)

    @staticmethod
    def _make_ok_response(gsm_accession: str):
        geo_response = "\n".join([f"^SAMPLE = {gsm_accession}", "!Sample_title = Sample Title",
                                  f"!Sample_geo_accession = {gsm_accession}", "!Sample_series_id = GSE12345"])
        return create_mock_response(geo_response, 200)

    @staticmethod
    def _make_error_response():
        return create_mock_response("ERROR", 500)

    @parameterized.expand([
        (["GSM123456"], ["GSM123456"]),
        ([], []),
        (["GSM100", "GSM200"], ["GSM100", "GSM200"]),
    ])
    def test_load_gsms_success(self, gsm_accessions: List[str], expected_ids: List[str]):
        self.mock_session.get.side_effect = [self._make_ok_response(accession) for accession in gsm_accessions]

        gsms: List[GSM] = self.loader.get_gsms(gsm_accessions)
        gsm_ids = [g.gsm for g in gsms]
        self.assertListEqual(gsm_ids, expected_ids)

        self.assertEqual(self.mock_session.get.call_count, len(gsm_accessions))
        self.assertEqual(self.repository.save_gsms.call_count, 1)
        save_args, _ = self.repository.save_gsms.call_args
        self.assertEqual(len(save_args[0]), len(gsm_accessions))

    def test_load_gsms_http_error(self):
        self.mock_session.get.return_value = self._make_error_response()

        with self.assertRaises(GEOError):
            self.loader.get_gsms(["GSM12345"])

        self.mock_session.get.assert_called_once()

    def test_load_gsms_connection_failure(self):
        req_exc = requests.RequestException()
        req_exc.response = create_mock_response("", 408)
        self.mock_session.get.side_effect = req_exc

        with self.assertRaises(GEOError):
            self.loader.get_gsms(["GSM99999"])

        self.mock_session.get.assert_called_once()
