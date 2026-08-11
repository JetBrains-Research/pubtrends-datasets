from dataclasses import dataclass


@dataclass
class PaginatedDatasets:
    """Class representing paginated search results for datasets."""
    total: int
    gse_accessions: list[str]
