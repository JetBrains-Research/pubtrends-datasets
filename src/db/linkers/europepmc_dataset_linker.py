from typing import List, Dict
import requests
from src.exception.europepmc_error import EuropePMCError
from src.db.linkers.paper_dataset_linker import PaperDatasetLinker


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
        # Use the mapped version and flatten results
        mapping = self.link_to_datasets_mapped(pubmed_ids)

        # Collect all accessions from all PubMed IDs
        all_accessions = []
        for accessions in mapping.values():
            all_accessions.extend(accessions)

        # Deduplicate and return
        return list(set(all_accessions))

    def link_to_datasets_mapped(self, pubmed_ids: List[str]) -> Dict[str, List[str]]:
        """
        Returns a mapping of PubMed IDs to their associated GEO accessions.

        Uses the EuropePMC API's batching capability while maintaining per-PubMed-ID
        mapping by parsing the 'extId' field in the response.

        :param pubmed_ids: List of PubMed IDs for which to get associated GEO accessions.
        :return: Dictionary mapping each PubMed ID to its list of GEO accessions.
        """
        if not pubmed_ids:
            raise ValueError("At least one valid PubMed ID is required")

        # Initialize result with empty lists for all PubMed IDs
        result: Dict[str, List[str]] = {pid: [] for pid in pubmed_ids}

        batch_size = EuropePMCDatasetLinker.BATCH_SIZE
        batches = [
            pubmed_ids[i: i + batch_size]
            for i in range(0, len(pubmed_ids), batch_size)
        ]

        for batch in batches:
            batch_mapping = self._fetch_geo_accession_batch_mapped(batch)
            # Merge batch results into overall result
            for pubmed_id, accessions in batch_mapping.items():
                if pubmed_id in result:
                    accessions_gse_only = filter(lambda acc: acc.startswith("GSE"), accessions)
                    result[pubmed_id].extend(accessions_gse_only)

        # Deduplicate accessions for each PubMed ID
        for pubmed_id in result:
            result[pubmed_id] = list(set(result[pubmed_id]))

        return result

    def _fetch_geo_accession_batch_mapped(self, pubmed_ids: List[str]) -> Dict[str, List[str]]:
        """
        Fetches GEO references in a list of papers (max 8 papers) from EuropePMC's
        annotations API, maintaining the mapping between PubMed IDs and their accessions.

        :param pubmed_ids: PubMed IDs of the papers for which to fetch GEO dataset accessions.
        :return: Dictionary mapping PubMed IDs to lists of GEO accessions.
        """
        article_ids = ",".join([f"MED:{pubmed_id}" for pubmed_id in pubmed_ids])
        result: Dict[str, List[str]] = {pid: [] for pid in pubmed_ids}

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

            # Parse response and maintain mapping using extId field
            for article in pmc_response.json():
                pubmed_id = article.get("extId")
                if pubmed_id and pubmed_id in result:
                    accessions = [
                        annotation["exact"]
                        for annotation in article.get("annotations", [])
                    ]
                    result[pubmed_id].extend(accessions)

            return result
        except requests.HTTPError as e:
            raise EuropePMCError(
                f"EuropePMC Annotations API status {e.response.status_code}"
            )
        except requests.RequestException:
            raise EuropePMCError("Network error during EuropePMC API call")
        except KeyError:
            raise EuropePMCError("Malformed response from EuropePMC API")
