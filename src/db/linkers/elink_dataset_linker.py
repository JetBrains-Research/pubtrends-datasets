import logging
from typing import List, Dict
import re
import requests
import tenacity

from src.db.linkers.paper_dataset_linker import PaperDatasetLinker
from src.exception.entrez_error import EntrezError

logger = logging.getLogger(__name__)


class ELinkDatasetLinker(PaperDatasetLinker):
    ELINK_REQUEST_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi"
    EFETCH_REQUEST_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    NUMBER_OF_RETRIES = 3

    def __init__(self, http_session: requests.Session):
        self.http_session = http_session

    def link_to_datasets(self, pubmed_ids: List[str]) -> List[str]:
        if not pubmed_ids:
            raise ValueError("At least one valid PubMed ID is required")
        geo_ids = self._fetch_geo_ids(pubmed_ids)
        return self._fetch_geo_accessions(geo_ids)

    def link_to_datasets_mapped(self, pubmed_ids: List[str]) -> Dict[str, List[str]]:
        """
        Returns a mapping of PubMed IDs to their associated GEO accessions.

        Since the ELink API doesn't support per-PubMed-ID mapping in batch mode,
        this implementation makes one API call per PubMed ID to maintain accuracy.

        :param pubmed_ids: List of PubMed IDs for which to get associated GEO accessions.
        :return: Dictionary mapping each PubMed ID to its list of GEO accessions.
        """
        if not pubmed_ids:
            raise ValueError("At least one valid PubMed ID is required")

        result: Dict[str, List[str]] = {}

        for pubmed_id in pubmed_ids:
            try:
                # Call link_to_datasets for each individual PubMed ID
                accessions = self.link_to_datasets([pubmed_id])
                result[pubmed_id] = accessions
            except Exception:
                # If a single ID fails, store empty list and continue
                logging.exception(f"Error linking PubMed ID {pubmed_id}")
                result[pubmed_id] = []

        return result

    @tenacity.retry(wait=tenacity.wait_exponential(max=10), stop=tenacity.stop_after_attempt(NUMBER_OF_RETRIES),
                    before_sleep=tenacity.before_sleep_log(logger, logging.WARNING), reraise=True)
    def _fetch_geo_ids(self, pubmed_ids: List[str]) -> List[str]:
        """
        Fetches GEO dataset ids for papers with the specified PubMed IDs.
        These IDs cannot be directly used to fetch the datasets themselves but
        can be translated to GEO accessions, which are then used to fetch the
        actual datasets.

        :param pubmed_ids: List of PubMed IDs to fetch GEO dataset ids for.
        :returns: A list that contains the IDs of the GEO datasets associated with the PubMed IDs.
        """
        try:
            response = self.http_session.post(
                ELinkDatasetLinker.ELINK_REQUEST_URL,
                params={
                    "dbfrom": "pubmed",
                    "db": "gds",
                    "linkname": "pubmed_gds",
                    "retmode": "json",
                },
                data={
                    "id": ",".join(pubmed_ids),
                }
            )
            response.raise_for_status()
            response = response.json()
            if "ERROR" in response:
                raise EntrezError("Error when fetching GEO IDs")

            linksets = response.get("linksets")
            if not linksets:
                return []
            linkset_dbs = linksets[0].get("linksetdbs")
            if not linkset_dbs:
                return []
            return linkset_dbs[0].get("links", [])
        except requests.HTTPError as e:
            raise EntrezError(f"ELink status {e.response.status_code}")
        except requests.RequestException:
            raise EntrezError("Network error during ELink API call")

    @tenacity.retry(wait=tenacity.wait_exponential(max=10), stop=tenacity.stop_after_attempt(NUMBER_OF_RETRIES),
                    before_sleep=tenacity.before_sleep_log(logger, logging.WARNING), reraise=True)
    def _fetch_geo_accessions(self, geo_ids: List[str]) -> List[str]:
        """
        Fetches GEO accessions for the given GEO IDs from the NCBI E-Utilities.

        :param geo_ids: GEO dataset IDs for which to fetch accessions.
        :return: List of GEO accessions in the same order.
        """
        try:
            response = self.http_session.post(
                ELinkDatasetLinker.EFETCH_REQUEST_URL,
                params={"db": "gds"},
                data={"id": ",".join(geo_ids)}
            )
            response.raise_for_status()
            geo_summaries = response.text

            # Series are the only type of GEO entry that contain all the infromation
            # we are looking for. Therefore we need to search for series accessions,
            # which begin with GSE.
            return re.findall("Accession: (GSE\\d+)", geo_summaries)
        except requests.HTTPError as e:
            raise EntrezError(f"EFetch status {e.response.status_code}")
        except requests.RequestException:
            raise EntrezError("Network error during EFetch API call")
