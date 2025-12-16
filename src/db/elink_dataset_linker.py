from typing import List
import re
import requests
from src.db.paper_dataset_linker import PaperDatasetLinker
from src.exception.entrez_error import EntrezError


class ELinkDatasetLinker(PaperDatasetLinker):
    ELINK_REQUEST_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi"
    EFETCH_REQUEST_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

    def __init__(self, http_session: requests.Session):
        self.http_session = http_session

    def link_to_datasets(self, pubmed_ids: List[str]) -> List[str]:
        if not pubmed_ids:
            raise ValueError("At least one valid PubMed ID is required")
        geo_ids = self._fetch_geo_ids(pubmed_ids)
        return self._fetch_geo_accessions(geo_ids)

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

    def _fetch_geo_accessions(self, geo_ids: List[str]) -> List[str]:
        """
        Fetches GEO accessions for the given GEO IDs from the NCBI E-Utilities.

        :param geo_ids: GEO dataset IDs for which to fetch accessions.
        :return: List of GEO accessions in the same order.
        """
        try:
            response = self.http_session.get(
                ELinkDatasetLinker.EFETCH_REQUEST_URL,
                params={"db": "gds", "id": ",".join(geo_ids)},
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
