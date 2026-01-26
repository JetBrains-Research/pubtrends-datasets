from typing import List, Dict

from src.db.gse import GSE
from src.db.gse_loader import GSELoader


class ChainedGSELoader(GSELoader):
    """
    Chain-of-Responsibility GSE loader that tries multiple loaders in order
    (e.g., GEOmetadb first, then NCBI, etc.). Each loader is queried only for
    accessions that remain unresolved by the previous loaders.
    """

    def __init__(self, *loaders: GSELoader) -> None:
        if not loaders:
            raise ValueError("At least one GSELoader must be provided")
        self.loaders: List[GSELoader] = list(loaders)

    def get_gses(self, gse_accessions: List[str]) -> List[GSE]:
        if not gse_accessions:
            return []

        found_map: Dict[str, GSE] = {}
        remaining: List[str] = list(dict.fromkeys(gse_accessions))

        for loader in self.loaders:
            if not remaining:
                break
            results = loader.get_gses(remaining)
            for g in results:
                if g and g.gse and g.gse not in found_map:
                    found_map[g.gse] = g
            remaining = [acc for acc in remaining if acc not in found_map]

        ordered_results: List[GSE] = [found_map[acc] for acc in gse_accessions if acc in found_map]
        return ordered_results
