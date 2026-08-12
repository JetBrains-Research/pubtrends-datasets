import datetime
import logging
import math
from typing import Optional

import requests
from tenacity import retry, wait_exponential, stop_after_attempt

from src.search.models import PaginatedDatasets

GSE_FILTER = "gse[ETYP]"

logger = logging.getLogger(__name__)


class DatasetSearchFilters:
    """Class for constructing search queries with filters."""

    def __init__(self, from_pub_date: datetime.date = datetime.date(2000, 1, 1),
                 to_pub_date: Optional[datetime.date] = None,
                 experiment_types: list[str] | None = None, from_update_date: datetime.date = datetime.date(2000, 1, 1),
                 to_update_date: Optional[datetime.date] = None):
        if experiment_types is None:
            experiment_types = []
        self.from_pub_date = from_pub_date
        self.to_pub_date = to_pub_date or datetime.date.today()
        self.from_update_date = from_update_date
        self.to_update_date = to_update_date or datetime.date.today()
        self.experiment_types = experiment_types

    def get_filter_term(self) -> str:
        filter_term = f"({self.from_pub_date.strftime('%Y/%m/%d')}:{self.to_pub_date.strftime('%Y/%m/%d')}[PDAT])"
        filter_term += f" AND ({self.from_update_date.strftime('%Y/%m/%d')}:{self.to_update_date.strftime('%Y/%m/%d')}[UDAT])"
        if self.experiment_types:
            processed_experiment_types = [f'"{experiment_type}"[DataSet Type]' for experiment_type in
                                          self.experiment_types]
            filter_term += f" AND ({' OR '.join(processed_experiment_types)})"
        return filter_term


class DatasetsSearch:
    """Class for searching for datasets via ESearch."""

    def __init__(self, session: requests.Session):
        self.session = session

    @retry(wait=wait_exponential(multiplier=1, min=1, max=10), stop=stop_after_attempt(3), reraise=True)
    def search(self, query: str, filters: DatasetSearchFilters, page: int = 1,
               page_size: int = 20) -> PaginatedDatasets:
        """
        Search for datasets via ESearch with pagination.

        :param query: The search query.
        :type query: str
        :param filters: The search filters.
        :type filters: DatasetSearchFilters
        :param page: The page number (starting from 1), defaults to 1.
        :type page: int, optional
        :param page_size: The number of items per page, defaults to 20.
        :type page_size: int, optional
        :return: Paginated search results containing total count and list of dataset IDs.
        :rtype: PaginatedDatasets
        """
        # Default to today; computed here rather than in the signature to avoid
        # being frozen to the date the function was first defined.
        base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        retstart = (page - 1) * page_size
        query = query.strip()
        term = f"{query} {'AND' if query else ''} {filters.get_filter_term()} AND {GSE_FILTER}"
        logger.info("Calling ESearch with query: %s", term)
        response = self.session.get(
            f"{base_url}",
            params={
                "db": "gds",
                "term": term,
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
        return PaginatedDatasets(total=count, gse_accessions=items, page=page, total_pages=math.ceil(count / page_size))
