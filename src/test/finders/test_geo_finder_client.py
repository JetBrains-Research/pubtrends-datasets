import unittest
from unittest.mock import Mock

import requests

from src.geofinder.geofinder_client import GeoFinderClient
from src.test.helpers.http import create_mock_response

MOCK_TABLE_RESPONSE = """
<table>
  <thead><tr><th>GSE ID</th><th>Title</th><th>Organism</th></tr></thead>
  <tbody>
    <tr><td>GSE111111</td><td>Dataset A</td><td>Homo sapiens</td></tr>
    <tr><td>GSE222222</td><td>Dataset B</td><td>Mus musculus</td></tr>
    <tr><td>GSE333333</td><td>Dataset C</td><td>Homo sapiens</td></tr>
  </tbody>
</table>
"""

MOCK_ERROR_ONE_ID = (
    'ERROR: The following ID(s) you entered are currently not available in GEOfinder: GSE999999. '
    'This could be because they are not valid GEO accession number(s) or that we have filtered '
    'them for some reason. Please remove the ID(s) from the search box and re-submit.'
)

MOCK_ERROR_TWO_IDS = (
    'ERROR: The following ID(s) you entered are currently not available in GEOfinder: GSE999999, GSE888888. '
    'This could be because they are not valid GEO accession number(s) or that we have filtered '
    'them for some reason. Please remove the ID(s) from the search box and re-submit.'
)


class TestGeoFinderClient(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_session = Mock()
        self.client = GeoFinderClient(http_session=self.mock_session)

    def test_get_similar_datasets_success(self) -> None:
        self.mock_session.post.return_value = create_mock_response(MOCK_TABLE_RESPONSE, 200)

        result = self.client.get_similar_datasets(['GSE203024', 'GSE116672'], count=10)

        self.assertEqual(result, ['GSE111111', 'GSE222222', 'GSE333333'])
        self.mock_session.post.assert_called_once()

    def test_get_similar_datasets_respects_count(self) -> None:
        self.mock_session.post.return_value = create_mock_response(MOCK_TABLE_RESPONSE, 200)

        result = self.client.get_similar_datasets(['GSE203024'], count=2)

        self.assertEqual(result, ['GSE111111', 'GSE222222'])

    def test_get_similar_datasets_retries_after_unavailable_id(self) -> None:
        self.mock_session.post.side_effect = [
            create_mock_response(MOCK_ERROR_ONE_ID, 200),
            create_mock_response(MOCK_TABLE_RESPONSE, 200),
        ]

        result = self.client.get_similar_datasets(['GSE203024', 'GSE999999'], count=10)

        self.assertEqual(result, ['GSE111111', 'GSE222222', 'GSE333333'])
        self.assertEqual(self.mock_session.post.call_count, 2)

    def test_get_similar_datasets_all_ids_unavailable_returns_empty(self) -> None:
        self.mock_session.post.return_value = create_mock_response(MOCK_ERROR_ONE_ID, 200)

        result = self.client.get_similar_datasets(['GSE999999'], count=10)

        self.assertEqual(result, [])
        self.mock_session.post.assert_called_once()

    def test_get_similar_datasets_multiple_unavailable_ids_retried(self) -> None:
        self.mock_session.post.side_effect = [
            create_mock_response(MOCK_ERROR_TWO_IDS, 200),
            create_mock_response(MOCK_TABLE_RESPONSE, 200),
        ]

        result = self.client.get_similar_datasets(['GSE203024', 'GSE999999', 'GSE888888'], count=10)

        self.assertEqual(result, ['GSE111111', 'GSE222222', 'GSE333333'])
        self.assertEqual(self.mock_session.post.call_count, 2)

    def test_get_similar_datasets_http_error_raises(self) -> None:
        self.mock_session.post.return_value = create_mock_response('Internal Server Error', 500)

        with self.assertRaises(requests.HTTPError):
            self.client.get_similar_datasets(['GSE203024'], count=10)

    def test_get_similar_datasets_network_error_raises(self) -> None:
        self.mock_session.post.side_effect = requests.RequestException('connection error')

        with self.assertRaises(requests.RequestException):
            self.client.get_similar_datasets(['GSE203024'], count=10)

    def test_get_similar_datasets_unexpected_error_format_returns_empty(self) -> None:
        self.mock_session.post.return_value = create_mock_response(
            'ERROR: Something completely unexpected happened', 200
        )

        result = self.client.get_similar_datasets(['GSE203024'], count=10)

        self.assertEqual(result, [])
        self.mock_session.post.assert_called_once()
