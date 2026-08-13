import datetime
from dataclasses import dataclass
from typing import Optional


class DatasetSearchFilters:
    """Class for constructing search queries with filters."""

    def __init__(self, from_pub_date: datetime.date = datetime.date(2000, 1, 1),
                 to_pub_date: Optional[datetime.date] = None,
                 experiment_types: list[str] | None = None, from_update_date: datetime.date = datetime.date(2000, 1, 1),
                 to_update_date: Optional[datetime.date] = None):
        if experiment_types is None:
            experiment_types = []
        self.from_pub_date = from_pub_date
        self.to_pub_date = to_pub_date or datetime.date.today()
        self.from_update_date = from_update_date
        self.to_update_date = to_update_date or datetime.date.today()
        self.experiment_types = experiment_types

    def get_filter_term(self) -> str:
        filter_term = f"({self.from_pub_date.strftime('%Y/%m/%d')}:{self.to_pub_date.strftime('%Y/%m/%d')}[PDAT])"
        filter_term += f" AND ({self.from_update_date.strftime('%Y/%m/%d')}:{self.to_update_date.strftime('%Y/%m/%d')}[UDAT])"
        if self.experiment_types:
            processed_experiment_types = [f'"{experiment_type}"[DataSet Type]' for experiment_type in
                                          self.experiment_types]
            filter_term += f" AND ({' OR '.join(processed_experiment_types)})"
        return filter_term


@dataclass
class PaginatedDatasets:
    """Class representing paginated search results for datasets."""
    total: int
    gse_accessions: list[str]
    page: int
    total_pages: int
