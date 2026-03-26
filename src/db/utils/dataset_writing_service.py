import asyncio

from src.db.repositories.gse_repository import GSERepository
from src.db.repositories.gsm_repository import GSMRepository
from src.db.utils.pipeline_models import ParsedDataset


class DatasetWritingService:
    """Service that batches parsed datasets and persists them to repositories."""

    def __init__(
            self,
            gse_repository: GSERepository,
            gsm_repository: GSMRepository,
    ) -> None:
        self.gse_repository = gse_repository
        self.gsm_repository = gsm_repository
        self._lock = asyncio.Lock()

    async def add(self, parsed_dataset: ParsedDataset) -> ParsedDataset:
        """
        Perists a parsed dataset to the database.

        :param parsed_dataset: Parsed dataset payload.
        :return: Parsed dataset payload.
        """
        async with self._lock:
            await asyncio.to_thread(self.gse_repository.save_gses, [parsed_dataset.gse])
            await asyncio.to_thread(self.gsm_repository.save_gsms, parsed_dataset.gsms)

        return parsed_dataset
