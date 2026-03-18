import asyncio
import threading
import time
from asyncio import shield

from src.db.models import GSE, GSM
from src.db.utils.pipeline_models import ParsedDataset

from src.db.repositories.gse_repository import GSERepository
from src.db.repositories.gsm_repository import GSMRepository


async def _periodic_flush(service: DatasetWritingService, interval: int) -> None:
    while True:
        await asyncio.sleep(interval)
        await service.flush()


class DatasetWritingService:
    """Service that batches parsed datasets and persists them to repositories."""

    def __init__(
        self,
        gse_repository: GSERepository,
        gsm_repository: GSMRepository,
        batch_size: int = 128,
    ) -> None:
        self.gse_repository = gse_repository
        self.gsm_repository = gsm_repository
        self.batch_size = batch_size
        self.batch: list[tuple[ParsedDataset, asyncio.Future[ParsedDataset]]] = []
        self._lock = asyncio.Lock()
        self.stop_event = threading.Event()
        self.flush_task = asyncio.create_task(_periodic_flush(self, 10))

    async def add(self, parsed_dataset: ParsedDataset) -> ParsedDataset:
        """
        Add one parsed dataset to the in-memory batch and flush on batch threshold.

        :param parsed_dataset: Parsed dataset payload.
        :return: Future that resolves with the written dataset after persistence.
        """
        future: asyncio.Future[ParsedDataset] = asyncio.get_event_loop().create_future()
        batch_to_flush: list[tuple[ParsedDataset, asyncio.Future[ParsedDataset]]] = []
        async with self._lock:
            self.batch.append((parsed_dataset, future))
            if len(self.batch) >= self.batch_size:
                batch_to_flush = self.batch
                self.batch = []
        if batch_to_flush:
            await self._write_batch(batch_to_flush)

        return await shield(future)

    async def flush(self) -> None:
        """Flush any remaining parsed datasets to repositories."""
        batch_to_flush: list[tuple[ParsedDataset, asyncio.Future[ParsedDataset]]] = []
        async with self._lock:
            if not self.batch:
                return
            batch_to_flush = self.batch
            self.batch = []

        await self._write_batch(batch_to_flush)

    async def _write_batch(
        self,
        batch: list[tuple[ParsedDataset, asyncio.Future[ParsedDataset]]],
    ) -> None:
        """
        Persist one batch of datasets and samples and resolve their futures.

        :param batch: List of (parsed_dataset, future) tuples.
        """
        gse_batch = [item[0].gse for item in batch]
        gsm_batch = [gsm for item in batch for gsm in item[0].gsms]

        await asyncio.to_thread(self.gse_repository.save_gses, gse_batch)
        await asyncio.to_thread(self.gsm_repository.save_gsms, gsm_batch)

        loop = asyncio.get_running_loop()
        for parsed_dataset, future in batch:
            loop.call_soon_threadsafe(future.set_result, parsed_dataset)

    def stop_flushing_thread(self) -> None:
        """Stop the periodic flushing thread."""
        self.flush_task.cancel()
