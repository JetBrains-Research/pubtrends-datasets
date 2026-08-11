import unittest
from unittest.mock import Mock
import requests
from src.search.datasets_esearch import DatasetsSearch, GSE_FILTER
from src.search.models import PaginatedDatasets
from src.test.helpers.http import create_mock_response


class TestDatasetsSearch(unittest.TestCase):
    def setUp(self):
        self.mock_session = Mock(spec=requests.Session)
        self.searcher = DatasetsSearch(self.mock_session)

    def test_search_success(self):
        mock_data = {
            "esearchresult": {
                "count": "2",
                "idlist": ["200116672", "200127884"]
            }
        }
        self.mock_session.get.return_value = create_mock_response(mock_data, 200)

        result = self.searcher.search("test query")

        self.assertEqual(result, PaginatedDatasets(total=2, gse_accessions=["GSE116672", "GSE127884"]))
        self.mock_session.get.assert_called_once_with(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            params={
                "db": "gds",
                "term": "test query" + GSE_FILTER,
                "retmode": "json",
                "retstart": 0,
                "retmax": 20
            }
        )

    def test_search_pagination(self):
        mock_data = {
            "esearchresult": {
                "count": "100",
                "idlist": ["200000001"]
            }
        }
        self.mock_session.get.return_value = create_mock_response(mock_data, 200)

        result = self.searcher.search("test query", page=2, page_size=10)

        self.assertEqual(result, PaginatedDatasets(total=100, gse_accessions=["GSE1"]))
        self.mock_session.get.assert_called_once_with(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            params={
                "db": "gds",
                "term": "test query" + GSE_FILTER,
                "retmode": "json",
                "retstart": 10,
                "retmax": 10
            }
        )

    def test_search_max_page_size(self):
        mock_data = {
            "esearchresult": {
                "count": "100",
                "idlist": []
            }
        }
        self.mock_session.get.return_value = create_mock_response(mock_data, 200)

        self.searcher.search("test query", page_size=2000)

        self.mock_session.get.assert_called_once_with(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            params={
                "db": "gds",
                "term": "test query" + GSE_FILTER,
                "retmode": "json",
                "retstart": 0,
                "retmax": 1000
            }
        )

    def test_search_error(self):
        self.mock_session.get.return_value = create_mock_response("Error", 500)

        with self.assertRaises(requests.HTTPError):
            self.searcher.search("test query")
