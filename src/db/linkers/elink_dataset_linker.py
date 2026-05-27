import logging
import re
import xml.etree.ElementTree as ET
from typing import List, Dict

import requests
import tenacity
from pyrate_limiter.limiter_factory import create_inmemory_limiter

from src.db.linkers.paper_dataset_linker import PaperDatasetLinker
from src.exception.entrez_error import EntrezError

logger = logging.getLogger(__name__)
eutilities_rate_limiter = create_inmemory_limiter()


class ELinkDatasetLinker(PaperDatasetLinker):
    ELINK_REQUEST_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi"
    EFETCH_REQUEST_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    ESUMMARY_REQUEST_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
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
        geo_ids = self._fetch_geo_ids(pubmed_ids)
        result: Dict[str, List[str]] = {pmid: [] for pmid in pubmed_ids}
        if not geo_ids:
            return result
        self._fetch_geo_accessions_mapped(geo_ids, result)
        return result

    @tenacity.retry(wait=tenacity.wait_exponential(max=10), stop=tenacity.stop_after_attempt(NUMBER_OF_RETRIES),
                    before_sleep=tenacity.before_sleep_log(logger, logging.WARNING), reraise=True)
    @eutilities_rate_limiter.as_decorator(name="e-utilities", weight=1)
    def _fetch_geo_accessions_mapped(self, geo_ids: List[str], pubmedIdToGSENumber: Dict[str, List[str]]) -> None:
        """
        Fetches GEO accessions for the given GEO IDs via eSummary and populates
        the result mapping from PubMed ID to GSE accession numbers.

        Each eSummary DocSum contains a ``PubMedIds`` list and an ``Accession``
        field. For every PubMed ID listed in a DocSum, the corresponding GSE
        accession is appended to ``result[pubmed_id]`` when that PubMed ID is
        already a key in *result*.

        :param geo_ids: GEO dataset IDs to summarise (``db=gds``).
        :param pubmedIdToGSENumber: Mutable mapping of PubMed ID → accession list to populate.
        """
        try:
            response = self.http_session.post(
                ELinkDatasetLinker.ESUMMARY_REQUEST_URL,
                params={"db": "gds"},
                data={"id": ",".join(geo_ids)},
            )
            response.raise_for_status()
            root = ET.fromstring(response.text)
            for doc_sum in root.findall("DocSum"):
                accession_item = doc_sum.find("Item[@Name='Accession'][@Type='String']")
                if accession_item is None or not (accession_item.text or "").startswith("GSE"):
                    continue
                for int_item in doc_sum.findall("Item[@Name='PubMedIds']/Item"):
                    pmid = int_item.text
                    if pmid and pmid in pubmedIdToGSENumber:
                        pubmedIdToGSENumber[pmid].append(accession_item.text)
        except ET.ParseError as e:
            raise EntrezError(f"Failed to parse eSummary XML: {e}")
        except requests.HTTPError as e:
            raise EntrezError(f"eSummary status {e.response.status_code}")
        except requests.RequestException:
            raise EntrezError("Network error during eSummary API call")

    @tenacity.retry(wait=tenacity.wait_exponential(max=10), stop=tenacity.stop_after_attempt(NUMBER_OF_RETRIES),
                    before_sleep=tenacity.before_sleep_log(logger, logging.WARNING), reraise=True)
    @eutilities_rate_limiter.as_decorator(name="e-utilities", weight=1)
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
    @eutilities_rate_limiter.as_decorator(name="e-utilities", weight=1)
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
