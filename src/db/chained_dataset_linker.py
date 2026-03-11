import logging
from typing import List, Dict

from src.db.paper_dataset_linker import PaperDatasetLinker

logger = logging.getLogger(__name__)


class ChainedDatasetLinker(PaperDatasetLinker):
    """
    Chain-of-responsibility dataset linker that queries multiple
    `PaperDatasetLinker` implementations and merges their results.

    - Calls each linker in order with the provided PubMed IDs.
    - Merges the returned GEO accessions.
    - Deduplicates while preserving the first-seen order across linkers.
    """

    def __init__(self, *linkers: PaperDatasetLinker) -> None:
        if not linkers:
            raise ValueError("At least one PaperDatasetLinker must be provided")
        self.linkers: List[PaperDatasetLinker] = list(linkers)

    def link_to_datasets(self, pubmed_ids: List[str]) -> List[str]:
        if not pubmed_ids:
            raise ValueError("At least one valid PubMed ID is required")

        seen = set()
        merged: List[str] = []

        for linker in self.linkers:
            try:
                accessions = linker.link_to_datasets(pubmed_ids) or []
            except Exception:
                # Fail-fast could be an option, but to keep the chain resilient,
                # skip failing linkers and proceed with others.
                logger.exception("Error linking papers to datasets")
                continue
            for acc in accessions:
                if acc not in seen:
                    seen.add(acc)
                    merged.append(acc)

        return merged

    def link_to_datasets_mapped(self, pubmed_ids: List[str]) -> Dict[str, List[str]]:
        """
        Returns a mapping of PubMed IDs to their associated GEO accessions.

        Queries each linker in the chain and merges the results per PubMed ID,
        deduplicating accessions while preserving order.

        :param pubmed_ids: List of PubMed IDs for which to get associated GEO accessions.
        :return: Dictionary mapping each PubMed ID to its list of GEO accessions.
        """
        if not pubmed_ids:
            raise ValueError("At least one valid PubMed ID is required")

        # Initialize result with empty lists for all PubMed IDs
        result: Dict[str, List[str]] = {pid: [] for pid in pubmed_ids}
        # Track seen accessions per PubMed ID for deduplication
        seen_per_id: Dict[str, set] = {pid: set() for pid in pubmed_ids}

        for linker in self.linkers:
            try:
                mapping = linker.link_to_datasets_mapped(pubmed_ids) or {}
            except Exception:
                # Fail-fast could be an option, but to keep the chain resilient,
                # skip failing linkers and proceed with others.
                logger.exception("Error linking papers to datasets")
                continue

            # Merge results from this linker into overall result
            for pubmed_id, accessions in mapping.items():
                if pubmed_id in result:
                    for acc in accessions:
                        if acc not in seen_per_id[pubmed_id]:
                            seen_per_id[pubmed_id].add(acc)
                            result[pubmed_id].append(acc)

        return result
