import logging
import re

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

GEOFINDER_URL = 'https://bioapps.byu.edu/geofinder/query'

CHECKBOX_DICT = (
    '{"Expression profiling by RT-PCR":"experimentType",'
    '"Expression profiling by array":"experimentType",'
    '"Expression profiling by high throughput sequencing":"experimentType",'
    '"Genome binding/occupancy profiling by genome tiling array":"experimentType",'
    '"Genome binding/occupancy profiling by high throughput sequencing":"experimentType",'
    '"Genome variation profiling by SNP array":"experimentType",'
    '"Genome variation profiling by genome tiling array":"experimentType",'
    '"Methylation profiling by array":"experimentType",'
    '"Methylation profiling by genome tiling array":"experimentType",'
    '"Methylation profiling by high throughput sequencing":"experimentType",'
    '"Non-coding RNA profiling by array":"experimentType",'
    '"Non-coding RNA profiling by high throughput sequencing":"experimentType",'
    '"Other":"experimentType",'
    '"Arabidopsis thaliana":"species",'
    '"Bos taurus":"species",'
    '"Caenorhabditis elegans":"species",'
    '"Danio rerio":"species",'
    '"Drosophila melanogaster":"species",'
    '"Escherichia coli":"species",'
    '"Gallus gallus":"species",'
    '"Homo sapiens":"species",'
    '"Mus musculus":"species",'
    '"Oryza sativa":"species",'
    '"Rattus norvegicus":"species",'
    '"Saccharomyces cerevisiae":"species",'
    '"Schizosaccharomyces pombe":"species",'
    '"Sus scrofa":"species",'
    '"synthetic construct":"species",'
    '"1-10":"numSamplesRange",'
    '"11-50":"numSamplesRange",'
    '"51-100":"numSamplesRange",'
    '"101-500":"numSamplesRange",'
    '"501-1000":"numSamplesRange",'
    '"1000+":"numSamplesRange"}'
)

_UNAVAILABLE_PATTERN = re.compile(
    r'are currently not available in GEOfinder:\s*(.*?)\.'
)


class GeoFinderClient:
    """Client for the GEO Finder service to find similar GEO datasets."""

    def __init__(self, http_session: requests.Session) -> None:
        """
        Initialize the GeoFinderClient.

        :param http_session: HTTP session to use for requests
        """
        self._session = http_session

    def get_similar_datasets(self, gse_ids: list[str], count: int) -> list[str]:
        """
        Fetch similar datasets for the given GSE IDs from GEO Finder.

        If some IDs are not available in GEO Finder, they are removed and the
        request is retried. Returns up to ``count`` similar GSE IDs.

        :param gse_ids: List of GSE IDs to find similar datasets for
        :param count: Maximum number of similar datasets to return
        :return: List of similar GSE IDs
        """
        active_ids = list(gse_ids)

        while active_ids:
            response_text = self._query(active_ids)

            if response_text.startswith('ERROR'):
                unavailable = _parse_unavailable_ids(response_text)
                if not unavailable:
                    logger.warning('GEO Finder returned unexpected error: %s', response_text)
                    return []
                active_ids = [gid for gid in active_ids if gid not in unavailable]
                continue

            return _parse_table(response_text)[:count]

        return []

    def _query(self, gse_ids: list[str]) -> str:
        """
        Send a query to the GEO Finder service.

        :param gse_ids: List of GSE IDs to query
        :return: Response text
        """
        data = {
            'searchSeries': '\n'.join(gse_ids),
            'checkboxDict': CHECKBOX_DICT,
            'startYear': '2001',
            'endYear': '2026',
        }
        headers = {
            'Accept': '*/*',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        }
        response = self._session.post(GEOFINDER_URL, data=data, headers=headers)
        response.raise_for_status()
        return response.text


def _parse_unavailable_ids(error_text: str) -> set[str]:
    """
    Parse unavailable GSE IDs from a GEO Finder error response.

    :param error_text: Error response text from GEO Finder
    :return: Set of unavailable GSE IDs
    """
    match = _UNAVAILABLE_PATTERN.search(error_text)
    if not match:
        return set()
    return {gid.strip() for gid in match.group(1).split(',') if gid.strip()}


def _parse_table(html_text: str) -> list[str]:
    """
    Parse GSE IDs from the first column of an HTML table response.

    :param html_text: HTML response containing a table of similar datasets
    :return: List of GSE IDs extracted from the first column
    """
    soup = BeautifulSoup(html_text, 'html.parser')
    gse_ids = []
    for row in soup.find_all('tr'):
        first_td = row.find('td')
        if first_td:
            content = first_td.get_text(strip=True)
            if content.startswith('GSE'):
                gse_ids.append(content)
    return gse_ids
