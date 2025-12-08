import unittest
from unittest.mock import Mock

import requests
from parameterized import parameterized

from src.db.europepmc_dataset_linker import EuropePMCDatasetLinker
from src.exception.europepmc_error import EuropePMCError

MOCK_EUROPEPMC_DATA = [
  {
    "source": "MED",
    "extId": "112233",
    "pmcid": "PMC112233",
    "annotations": [
      {
        "exact": "GSE12345",
      },
      {
        "exact": "GSE54321"
      }
    ]
  },
] 

class TestEuropePMCDatasetLinker(unittest.TestCase):
    def setUp(self):
        self.mock_europepmc_response = Mock()
        self.mock_europepmc_response.status_code = 200
        self.mock_europepmc_response.json.return_value = MOCK_EUROPEPMC_DATA

        self.mock_fail_response = Mock()
        self.mock_fail_response.status_code = 500
        self.mock_fail_response.json.return_value = "ERROR"
        self.mock_fail_response.raise_for_status.side_effect = requests.HTTPError()
        self.mock_fail_response.raise_for_status.side_effect.response = self.mock_fail_response

        self.mock_empty_response = Mock()
        self.mock_empty_response.status_code = 400
        self.mock_empty_response.raise_for_status.side_effect = requests.HTTPError()
        self.mock_empty_response.raise_for_status.side_effect.response = self.mock_empty_response

        self.mock_session = Mock()

        self.linker = EuropePMCDatasetLinker(http_session=self.mock_session)

    @parameterized.expand([
        (["112233"], ["GSE12345", "GSE54321"]),
        ([str(i) for i in range(EuropePMCDatasetLinker.BATCH_SIZE)] + ["112233"], ["GSE12345", "GSE54321"]), # Two batches
        (["112233"] * EuropePMCDatasetLinker.BATCH_SIZE, ["GSE12345", "GSE54321"]), # Two batches
    ])
    def test_link_papers_to_datasets_success(self, pubmed_ids, expected_geo_accessions):
        self.mock_session.get.return_value = self.mock_europepmc_response

        result = self.linker.link_to_datasets(pubmed_ids)
        
        self.assertCountEqual(result, expected_geo_accessions)
        number_of_pubmed_ids = len(pubmed_ids)
        number_of_batches = number_of_pubmed_ids // EuropePMCDatasetLinker.BATCH_SIZE + (1 if number_of_pubmed_ids % EuropePMCDatasetLinker.BATCH_SIZE else 0)
        assert self.mock_session.get.call_count == number_of_batches
    
    def test_link_papers_to_datasets_europepmc_failure(self):
        self.mock_session.get.return_value = self.mock_fail_response
        self.assertRaises(EuropePMCError, self.linker.link_to_datasets, ["112233"])
        self.mock_session.get.assert_called_once()

    def test_link_papers_to_datasets_empty_input(self):
        self.mock_session.get.return_value = self.mock_empty_response
        self.assertRaises(EuropePMCError, self.linker.link_to_datasets, ["112233"])
        self.mock_session.get.assert_called_once()

    def test_link_papers_to_datasets_connection_error(self):
        self.mock_session.get.side_effect = requests.RequestException
        self.assertRaises(EuropePMCError, self.linker.link_to_datasets, ["112233"])
        self.mock_session.get.assert_called_once()
      

        
        
        