from abc import ABCMeta
from abc import abstractmethod
from typing import List, Dict


class PaperDatasetLinker(metaclass=ABCMeta):
    @abstractmethod
    def link_to_datasets(self, pubmed_ids: List[str]) -> List[str]:
        """
        Returns a list GEO accessions (GSExxx) for datasets associated with
        the articles provided by the list of PubMed IDs.

        :param pubmed_ids: List of Pubmed IDs for which to get associtated GEO acessions.
        :type pubmed_ids: List[str]
        :return: List GEO accessions for datasets associated with the articles
        provided by the list of PubMed IDs.
        :rtype: List[str]
        """
        pass

    def link_to_datasets_mapped(self, pubmed_ids: List[str]) -> Dict[str, List[str]]:
        """
        Returns a mapping of PubMed IDs to their associated GEO accessions.

        This method maintains the relationship between each PubMed ID and its
        associated GEO dataset accessions.

        Default implementation calls link_to_datasets() and returns the same
        accessions for all PubMed IDs (losing the mapping). Subclasses should
        override this to provide accurate per-PubMed-ID mappings.

        :param pubmed_ids: List of Pubmed IDs for which to get associated GEO accessions.
        :type pubmed_ids: List[str]
        :return: Dictionary mapping PubMed IDs to lists of GEO accessions.
        :rtype: Dict[str, List[str]]
        """
        accessions = self.link_to_datasets(pubmed_ids)
        # Default: return same accessions for all IDs (inaccurate but maintains interface)
        return {pid: accessions for pid in pubmed_ids}
