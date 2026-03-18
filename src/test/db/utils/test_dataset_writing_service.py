import asyncio
import unittest
from unittest.mock import Mock

from src.db.models import GSE, GSM
from src.db.utils.dataset_writing_service import DatasetWritingService
from src.db.utils.pipeline_models import ParsedDataset


class TestDatasetWritingService(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def _parsed_dataset(accession: str) -> ParsedDataset:
        return ParsedDataset(
            accession=accession,
            archive_path=f"/tmp/{accession}.soft.gz",
            gse=GSE(gse=accession),
            gsms=[GSM(gsm=f"{accession}_GSM1", series_id=accession)],
        )

    async def test_add_flushes_on_batch_size(self) -> None:
        gse_repository = Mock()
        gsm_repository = Mock()
        writer = DatasetWritingService(gse_repository, gsm_repository)

        future1 = writer.add(self._parsed_dataset("GSE1"))
        gse_repository.save_gses.assert_not_called()
        gsm_repository.save_gsms.assert_not_called()

        future2 = writer.add(self._parsed_dataset("GSE2"))
        await asyncio.gather(future1, future2)
        gse_repository.save_gses.assert_called_once()
        gsm_repository.save_gsms.assert_called_once()

    async def test_flush_persists_remaining_items(self) -> None:
        gse_repository = Mock()
        gsm_repository = Mock()
        writer = DatasetWritingService(gse_repository, gsm_repository)

        task = writer.add(self._parsed_dataset("GSE1"))
        await task

        gse_repository.save_gses.assert_called_once()
        gsm_repository.save_gsms.assert_called_once()
