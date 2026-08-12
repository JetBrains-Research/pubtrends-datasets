import datetime
import unittest
from unittest.mock import Mock
import requests
from src.search.datasets_esearch import DatasetsSearch, GSE_FILTER, DatasetSearchFilters
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

        filter = DatasetSearchFilters()
        result = self.searcher.search("test query", filter)

        self.assertEqual(result, PaginatedDatasets(total=2, gse_accessions=["GSE116672", "GSE127884"], page=1, total_pages=1))
        self.mock_session.get.assert_called_once_with(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            params={
                "db": "gds",
                "term": f"test query AND {filter.get_filter_term()} AND {GSE_FILTER}",
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

        filter = DatasetSearchFilters()
        result = self.searcher.search("test query", filters=filter, page=2, page_size=10)

        self.assertEqual(result, PaginatedDatasets(total=100, gse_accessions=["GSE1"], page=2, total_pages=10))
        self.mock_session.get.assert_called_once_with(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            params={
                "db": "gds",
                "term": f"test query AND {filter.get_filter_term()} AND {GSE_FILTER}",
                "retmode": "json",
                "retstart": 10,
                "retmax": 10
            }
        )

    def test_search_error(self):
        self.mock_session.get.return_value = create_mock_response("Error", 500)

        with self.assertRaises(requests.HTTPError):
            self.searcher.search("test query", filters=DatasetSearchFilters())


    def test_filter_term(self):
        filter = DatasetSearchFilters(
            from_pub_date=datetime.date(2022, 1, 1),
            to_pub_date=datetime.date(2022, 12, 31),
            from_update_date=datetime.date(2023, 1, 1),
            to_update_date=datetime.date(2023, 12, 31),
            experiment_types=["type 1", "type 2"]
        )

        self.assertEqual(filter.get_filter_term(), '(2022/01/01:2022/12/31[PDAT]) AND (2023/01/01:2023/12/31[UDAT]) AND ("type 1"[DataSet Type] OR "type 2"[DataSet Type])')
