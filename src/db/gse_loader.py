from abc import ABCMeta, abstractmethod
from typing import Iterable, List
from src.db.gse import GSE


class GSELoader(metaclass=ABCMeta):
    @abstractmethod
    def get_gses(self, gse_accessions: Iterable[str]) -> List[GSE]:
        """
        Returns GSE objects associated with the GEO series with the acession
        numbers provided in the list

        :param gse_accessions: Accession numbers of the GEO series to load.
        :type gse_accessions: List[str] 
        :return: GSE objects representing the series.
        :rtype: List[GSE]
        """
        pass
