import unittest
from unittest.mock import Mock

import requests

from src.db.elink_dataset_linker import ELinkDatasetLinker
from src.exception.entrez_error import EntrezError

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
        self.mock_elink_response = Mock()
        self.mock_elink_response.status_code = 200
        self.mock_elink_response.json.return_value = MOCK_ELINK_DATA

        self.mock_fail_response = Mock()
        self.mock_fail_response.status_code = 500
        self.mock_fail_response.json.return_value = "ERROR"
        self.mock_fail_response.raise_for_status.side_effect = requests.HTTPError()
        self.mock_fail_response.raise_for_status.side_effect.response = self.mock_fail_response

        self.mock_efetch_response = Mock()
        self.mock_efetch_response.status_code = 200
        self.mock_efetch_response.text = MOCK_EFETCH_DATA
        self.mock_session = Mock()

        self.linker = ELinkDatasetLinker(http_session=self.mock_session)

    def test_fetch_geo_ids_success(self):
        self.mock_session.post.return_value = self.mock_elink_response

        self.linker = ELinkDatasetLinker(http_session=self.mock_session)

        pubmed_ids = ["112233"]
        result = self.linker._fetch_geo_ids(pubmed_ids)

        expected_result = ["12345", "67890"]

        self.assertListEqual(result, expected_result)

    def test_fetch_geo_accessions_success(self):
        self.mock_session.get.return_value = self.mock_efetch_response

        pubmed_ids = ["112233"]
        result = self.linker._fetch_geo_accessions(pubmed_ids)

        expected_result = ["GSE12345", "GSE54321"]

        self.assertListEqual(result, expected_result)

    def test_link_papers_to_datasets_success(self):
        self.mock_session.post.return_value = self.mock_elink_response
        self.mock_session.get.return_value = self.mock_efetch_response

        pubmed_ids = ["112233"]
        result = self.linker.link_to_datasets(pubmed_ids)

        expected_result = ["GSE12345", "GSE54321"]

        self.assertListEqual(result, expected_result)

    def test_link_papers_to_datasets_elink_server_error(self):
        self.mock_session.post.return_value = self.mock_fail_response
        self.assertRaises(EntrezError, self.linker.link_to_datasets, ["112233"])
        self.mock_session.post.assert_called_once()
        self.mock_session.get.assert_not_called()

    def test_link_papers_to_datasets_efetch_server_error(self):
        self.mock_session.post.return_value = self.mock_elink_response
        self.mock_session.get.return_value = self.mock_fail_response

        self.assertRaises(EntrezError, self.linker.link_to_datasets, ["112233"])
        self.mock_session.post.assert_called_once()
        self.mock_session.get.assert_called_once()

    def test_link_papers_to_datasets_elink_network_failure(self):
        self.mock_session.post.side_effect = requests.RequestException
        self.assertRaises(EntrezError, self.linker.link_to_datasets, ["112233"])
        self.mock_session.post.assert_called_once()
        self.mock_session.get.assert_not_called()

    def test_link_papers_to_datasets_efetch_network_failure(self):
        self.mock_session.post.return_value = self.mock_elink_response
        self.mock_session.get.side_effect = requests.RequestException

        self.assertRaises(EntrezError, self.linker.link_to_datasets, ["112233"])
        self.mock_session.post.assert_called_once()
        self.mock_session.get.assert_called_once()

    def test_link_papers_to_datasets_empty_input(self):
        self.assertRaises(ValueError, self.linker.link_to_datasets, [])
        self.mock_session.post.assert_not_called()
        self.mock_session.get.assert_not_called()
