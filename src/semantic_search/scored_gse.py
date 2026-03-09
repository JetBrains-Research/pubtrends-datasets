from dataclasses import dataclass

from src.db.gse import GSE


@dataclass
class ScoredGSE:
    gse: GSE
    score: float