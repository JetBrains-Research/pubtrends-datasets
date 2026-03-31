from dataclasses import dataclass


@dataclass
class ScoredGSE:
    gse_accession: str
    score: float
