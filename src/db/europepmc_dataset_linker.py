from typing import List
import requests
from src.exception.europepmc_error import EuropePMCError
from src.db.paper_dataset_linker import PaperDatasetLinker
import itertools


class EuropePMCDatasetLinker(PaperDatasetLinker):
    EUROPEPMC_URL = (
        "https://www.ebi.ac.uk/europepmc/annotations_api/annotationsByArticleIds"
    )
    BATCH_SIZE = 8

    def __init__(self, http_session: requests.Session):
        self.http_session = http_session

    def link_to_datasets(self, pubmed_ids: List[str]) -> List[str]:
        """
        Fetches GEO accessions for several PubMed IDs from the EuropePMC database.

        :param pubmed_ids: PubMed IDs of the papers for which to fetch GEO dataset
        accessions.
        :return: List of GEO acessions associated with the papers.
        """
        # There is no explicit rate limit for EuropePMC
        if not pubmed_ids:
            raise ValueError("At least one valid PubMed ID is required")
        batch_size = EuropePMCDatasetLinker.BATCH_SIZE
        batches = [
            pubmed_ids[i : i + batch_size]
            for i in range(0, len(pubmed_ids), batch_size)
        ]
        accession_batches = (
            self._fetch_geo_accession_batch(batch) for batch in batches
        )
        accessions = itertools.chain.from_iterable(accession_batches)
        # There may multiple annotations for the same GEO accession
        return list(set(accessions))

    def _fetch_geo_accession_batch(self, pubmed_ids: List[str]) -> List[str]:
        """
        Fetches GEO references in a list of papers (max 8 papers) from EuropePMC's
        annotations API.

        :param pubmed_ids: PubMed IDs of the papers for which to fetch GEO dataset
        accessions.
        :return: List of GEO acessions associated with the papers.
        """
        article_ids = ",".join([f"MED:{pubmed_id}" for pubmed_id in pubmed_ids])
        try:
            pmc_response = self.http_session.get(
                EuropePMCDatasetLinker.EUROPEPMC_URL,
                params={
                    "articleIds": article_ids,
                    "type": "Accession Numbers",
                    "subType": "geo",
                    "format": "json",
                },
            )
            pmc_response.raise_for_status()
            accessions = [
                annotation["exact"]
                for article in pmc_response.json()
                for annotation in article["annotations"]
            ]
            return accessions
        except requests.HTTPError as e:
            raise EuropePMCError(
                f"EuropePMC Annotations API status {e.response.status_code}"
            )
        except requests.RequestException:
            raise EuropePMCError("Network error during EuropePMC API call")
        except KeyError:
            raise EuropePMCError("Malformed response from EuropePMC API")
            
