import logging
from typing import List

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
