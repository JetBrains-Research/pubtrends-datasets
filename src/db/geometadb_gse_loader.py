from typing import List

from src.config.config import Config
from src.db.gse import GSE
from src.db.gse_loader import GSELoader
from src.db.gse_repository import GSERepository


class GEOmetadbGSELoader(GSELoader):
    def __init__(self, repository: GSERepository) -> None:
        self.repository = repository

    def load_gses(self, gse_accessions: List[str]) -> List[GSE]:
        return self.repository.get_gses(gse_accessions)
