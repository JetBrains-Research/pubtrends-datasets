from dataclasses import dataclass

from src.db.models import GSE, GSM


@dataclass(frozen=True)
class DownloadedArchive:
    """Downloaded GEO archive metadata passed from download stage to parse stage."""

    accession: str
    archive_path: str


@dataclass(frozen=True)
class ParsedDataset:
    """Parsed GEO dataset payload passed from parse stage to save stage."""

    accession: str
    archive_path: str
    gse: GSE
    gsms: list[GSM]
