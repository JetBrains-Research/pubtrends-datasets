import datetime
from typing import List
import requests

from src.search import DatasetsSearch
from src.search.datasets_esearch import DatasetSearchFilters


def get_gse_ids_by_last_update_date(start_date: datetime.date, end_date: datetime.date) -> List[str]:
    """
    Find GSE which were last updated during given period.
    :param start_date: date from which you want to search gse ids (e.g., "2019/12/02")
    :param end_date: date until you want to search gse ids (e.g., "2019/12/05")
    :return: GSE ids corresponding to request
    """
    with requests.Session() as session:
        searcher = DatasetsSearch(session)
        gse_ids = []
        filters = DatasetSearchFilters(from_update_date=start_date, to_update_date=end_date)
        page_size = 50000

        search_result = searcher.search("", filters, page_size=page_size, page=1)
        while search_result.page <= search_result.total_pages:
            gse_ids.extend([gse_accession for gse_accession in search_result.gse_accessions])
            search_result = searcher.search("", filters, page_size=page_size, page=search_result.page + 1)

        return gse_ids


if __name__ == "__main__":
    ids = get_gse_ids_by_last_update_date(datetime.date(2025, 10, 1), datetime.date(2025, 10, 3))
    for geo_id in ids:
        print(f"ftp://ftp.ncbi.nlm.nih.gov/geo/series/{geo_id[:-3]}nnn/{geo_id}/soft/{geo_id}_family.soft.gz")
