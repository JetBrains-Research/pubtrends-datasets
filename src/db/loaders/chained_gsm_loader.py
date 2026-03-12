from typing import List, Dict

from src.db.models.gsm import GSM
from src.db.loaders.gsm_loader import GSMLoader


class ChainedGSMLoader(GSMLoader):
    """
    Chain-of-Responsibility GSM loader that tries multiple loaders in order
    (e.g., GEOmetadb first, then NCBI, etc.). Each loader is queried only for
    accessions that remain unresolved by the previous loaders.
    """

    def __init__(self, *loaders: GSMLoader) -> None:
        if not loaders:
            raise ValueError("At least one GSMLoader must be provided")
        self.loaders: List[GSMLoader] = list(loaders)

    def get_gsms(self, gsm_accessions: List[str]) -> List[GSM]:
        if not gsm_accessions:
            return []

        found_map: Dict[str, GSM] = {}
        remaining: List[str] = list(dict.fromkeys(gsm_accessions))

        for loader in self.loaders:
            if not remaining:
                break
            results = loader.get_gsms(remaining)
            for g in results:
                if g and g.gsm and g.gsm not in found_map:
                    found_map[g.gsm] = g
            remaining = [acc for acc in remaining if acc not in found_map]

        ordered_results: List[GSM] = [found_map[acc] for acc in gsm_accessions if acc in found_map]
        return ordered_results
