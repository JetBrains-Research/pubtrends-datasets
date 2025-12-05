from abc import ABCMeta
from abc import abstractmethod
from typing import List

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