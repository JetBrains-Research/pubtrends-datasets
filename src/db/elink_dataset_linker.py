from typing import List
import re
import requests
from src.db.paper_dataset_linker import PaperDatasetLinker
from src.exception.entrez_error import EntrezError

class ELinkDatasetLinker(PaperDatasetLinker):
    def __init__(self, http_session: requests.Session):
        self.elink_request_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi"
        self.efetch_request_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        self.http_session = http_session
    
    def link_to_datasets(self, pubmed_ids: List[str]) -> List[str]:
        geo_ids = self._fetch_geo_ids(pubmed_ids)
        return self._fetch_geo_accessions(geo_ids)

    def _fetch_geo_ids(self, pubmed_ids: List[str]) -> List[str]:
        """
        Fetches GEO dataset ids for papers with the specified PubMed IDs.

        :param pubmed_ids: List of PubMed IDs to fetch GEO dataset ids for.
        :returns: A list that contains the IDs of the GEO datasets associated with the PubMed IDs.
        """
        response = self.http_session.post(
        self.elink_request_url,
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
        if response.status_code != 200:
            raise EntrezError(f"ELink status {response.status_code}")
        response = response.json()
        if "ERROR" in response:
            raise EntrezError("Error when fetching GEO IDs")

        linksets = response.get("linksets")
        if not linksets:
            return[]
        linkset_dbs = linksets[0].get("linksetdbs")
        if not linkset_dbs:
            return []
        return linkset_dbs[0].get("links", [])

    def _fetch_geo_accessions(self, geo_ids: List[str]) -> List[str]:
        """
        Fetches GEO accessions for the given GEO IDs from the NCBI E-Utilities.

        :param geo_ids: GEO dataset IDs for which to fetch accessions.
        :return: List of GEO accessions in the same order.
        """
        response = self.http_session.get(
            self.efetch_request_url,
            params={"db": "gds", "id": ",".join(geo_ids)},
        )
        if response.status_code != 200:
            raise EntrezError(f"ESearch status {response.status_code}")
        geo_summaries = response.text

        # Series are the only type of GEO entry that contain all of the infromation
        # we are looking for. Therefore we need to search for series accessions,
        # which begin with GSE.
        return re.findall("Accession: (GSE\\d+)", geo_summaries)

