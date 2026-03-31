import asyncio
from typing import Iterable, List

from src.config.config import Config
from src.db.loaders import GSELoader
from src.db.models import GSE
from src.db.repositories import GSERepository
from src.db.repositories.gsm_repository import GSMRepository
from src.db.utils.backfill_geometadb import GEOmetadbBackfiller


class GEOmetadbBackfillerGSELoader(GSELoader):
    """
    Loader for GSE data that uses the GEOmetadb backfilling script to fetch the data.
    """

    def __init__(
            self,
            config: Config,
            gse_repository: GSERepository,
            gsm_repository: GSMRepository,
    ):
        self.geometadb_backfiller = GEOmetadbBackfiller(config, gse_repository, gsm_repository)

    def get_gses(self, gse_accessions: Iterable[str]) -> List[GSE]:
        results = asyncio.run(self.geometadb_backfiller.download_datasets(gse_accessions, ignore_failures=True))
        return list(filter(lambda x: isinstance(x, GSE), results))
