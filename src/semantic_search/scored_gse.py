from dataclasses import dataclass

from src.db.models import GSE_DTO


@dataclass
class ScoredGSE:
    gse: GSE_DTO
    score: float
