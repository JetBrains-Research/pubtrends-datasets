from dataclasses import dataclass
from typing import List

from src.db.models import GSE, GSM


@dataclass
class GSEWithGSMs:
    gse: GSE
    gsms: List[GSM]
