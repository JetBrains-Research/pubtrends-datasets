from abc import ABCMeta, abstractmethod
from typing import Iterable, List
from src.db.models.gsm import GSM


class GSMLoader(metaclass=ABCMeta):
    @abstractmethod
    def get_gsms(self, gsm_accessions: Iterable[str]) -> List[GSM]:
        """
        Returns GSM objects associated with the GEO samples with the accession
        numbers provided in the list

        :param gsm_accessions: Accession numbers of the GEO samples to load.
        :type gsm_accessions: List[str]
        :return: GSM objects representing the samples.
        :rtype: List[GSM]
        """
        pass
