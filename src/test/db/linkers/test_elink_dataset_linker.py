import unittest
from typing import Any
from unittest.mock import Mock, ANY

import requests

from src.db.linkers.elink_dataset_linker import ELinkDatasetLinker
from src.exception.entrez_error import EntrezError
from src.test.helpers.http import create_mock_response

MOCK_ELINK_DATA = {
    "header": {},
    "linksets": [
        {
            "linksetdbs": [
                {"linkname": "pubmed_gds", "links": ["12345", "67890"]}
            ]
        }
    ]
}
MOCK_EFETCH_DATA = """
10. Title 1
(Submitter supplied) Summary 1
Organism:	Mus musculus
Type:		Expression profiling by high throughput sequencing
Platform: GPL21626 3072 Samples
FTP download: GEO (CSV, TSV) ftp://ftp.ncbi.nlm.nih.gov/...
SRA Run Selector: https://www.ncbi.nlm.nih.gov/...
Series		Accession: GSE12345	ID: 200127884

11. Title 2
(Submitter supplied) Summary 2
Organism:	Homo sapiens
Type:		Expression profiling by high throughput sequencing
Platforms: GPL24676 GPL18573 13127 Samples
FTP download: GEO (TSV) ftp://ftp.ncbi.nlm.nih.gov/...
SRA Run Selector: https://www.ncbi.nlm.nih.gov/...
Series		Accession: GSE54321	ID: 200116672
"""


class TestELinkDatasetLinker(unittest.TestCase):
    def setUp(self):
        self.mock_elink_response = create_mock_response(MOCK_ELINK_DATA, 200)
        self.mock_fail_response = create_mock_response("ERROR", 500)
        self.mock_efetch_response = create_mock_response(MOCK_EFETCH_DATA, 200)

        self.mock_session = Mock()

        self.linker = ELinkDatasetLinker(http_session=self.mock_session)
        self.post_kwargs = {"params": ANY, "data": ANY}

    def assert_elink_called(self):
        self.mock_session.post.assert_any_call(
            ELinkDatasetLinker.ELINK_REQUEST_URL,
            **self.post_kwargs
        )

    def assert_efetch_called(self):
        self.mock_session.post.assert_any_call(
            ELinkDatasetLinker.EFETCH_REQUEST_URL,
            **self.post_kwargs
        )

    def _mock_post_routes(
            self,
            elink: Mock | Exception | type[Exception],
            efetch: Mock | Exception | type[Exception]
    ) -> None:
        """
        Routes mocked POST requests by URL to a response or an exception.

        :param elink: Behavior for ELink requests.
        :param efetch: Behavior for EFetch requests.
        """
        routes = {
            ELinkDatasetLinker.ELINK_REQUEST_URL: elink,
            ELinkDatasetLinker.EFETCH_REQUEST_URL: efetch,
        }

        def side_effect(url: str, *_args: Any, **_kwargs: Any) -> Mock:
            if url not in routes:
                raise AssertionError(f"Unexpected URL: {url}")

            action = routes[url]
            if isinstance(action, type) and issubclass(action, Exception):
                raise action()
            if isinstance(action, Exception):
                raise action
            return action

        self.mock_session.post.side_effect = side_effect

    def test_fetch_geo_ids_success(self):
        self.mock_session.post.return_value = self.mock_elink_response

        pubmed_ids = ["112233"]
        result = self.linker._fetch_geo_ids(pubmed_ids)

        expected_result = ["12345", "67890"]

        self.assertListEqual(result, expected_result)

    def test_fetch_geo_accessions_success(self):
        self.mock_session.post.return_value = self.mock_efetch_response

        pubmed_ids = ["112233"]
        result = self.linker._fetch_geo_accessions(pubmed_ids)

        expected_result = ["GSE12345", "GSE54321"]

        self.assertListEqual(result, expected_result)

    def test_link_papers_to_datasets_success(self):
        self._mock_post_routes(
            elink=self.mock_elink_response,
            efetch=self.mock_efetch_response
        )

        pubmed_ids = ["112233"]
        result = self.linker.link_to_datasets(pubmed_ids)

        expected_result = ["GSE12345", "GSE54321"]

        self.assertListEqual(result, expected_result)
        self.assert_elink_called()
        self.assert_efetch_called()

    def test_link_papers_to_datasets_elink_server_error(self):
        self._mock_post_routes(
            elink=self.mock_fail_response,
            efetch=self.mock_efetch_response
        )
        self.assertRaises(EntrezError, self.linker.link_to_datasets, ["112233"])
        self.assert_elink_called()

    def test_link_papers_to_datasets_efetch_server_error(self):
        self._mock_post_routes(
            elink=self.mock_elink_response,
            efetch=self.mock_fail_response
        )

        self.assertRaises(EntrezError, self.linker.link_to_datasets, ["112233"])
        self.assert_elink_called()
        self.assert_efetch_called()

    def test_link_papers_to_datasets_elink_network_failure(self):
        self.mock_session.post.side_effect = requests.RequestException
        self.assertRaises(EntrezError, self.linker.link_to_datasets, ["112233"])
        self.assert_elink_called()

    def test_link_papers_to_datasets_efetch_network_failure(self):
        self._mock_post_routes(
            elink=self.mock_elink_response,
            efetch=requests.RequestException
        )

        self.assertRaises(EntrezError, self.linker.link_to_datasets, ["112233"])
        self.assert_elink_called()
        self.assert_efetch_called()

    def test_link_papers_to_datasets_empty_input(self):
        self.assertRaises(ValueError, self.linker.link_to_datasets, [])
        self.mock_session.post.assert_not_called()
