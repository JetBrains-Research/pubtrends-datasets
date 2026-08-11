import requests
from tenacity import retry, wait_exponential

from src.search.models import PaginatedDatasets

GSE_FILTER = " AND gse[ETYP]"


class DatasetsSearch:
    """Class for searching for datasets via ESearch."""

    def __init__(self, session: requests.Session):
        self.session = session

    @retry(wait=wait_exponential(multiplier=1, min=4, max=10))
    def search(self, query: str, page: int = 1, page_size: int = 20) -> PaginatedDatasets:
        """
        Search for datasets via ESearch with pagination.

        :param query: The search query.
        :type query: str
        :param page: The page number (starting from 1), defaults to 1.
        :type page: int, optional
        :param page_size: The number of items per page, defaults to 20.
        :type page_size: int, optional
        :return: Paginated search results containing total count and list of dataset IDs.
        :rtype: PaginatedDatasets
        """
        base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        page_size = min(page_size, 1000)
        retstart = (page - 1) * page_size
        response = self.session.get(
            f"{base_url}",
            params={
                "db": "gds",
                "term": query + GSE_FILTER,
                "retmode": "json",
                "retstart": retstart,
                "retmax": page_size
            }
        )
        response.raise_for_status()
        data = response.json()["esearchresult"]
        count = int(data.get("count", 0))
        uids = data.get("idlist", [])
        gse_uid_base = 200000000
        gsm_uid_base = 300000000
        items = ["GSE" + str(int(uid) - gse_uid_base) for uid in uids if gse_uid_base < int(uid) < gsm_uid_base]
        return PaginatedDatasets(total=count, gse_accessions=items)
