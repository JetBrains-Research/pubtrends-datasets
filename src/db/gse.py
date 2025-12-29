"""Gene Expression Omnibus Series (GSE) data model."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class GSE:
    """Gene Expression Omnibus Series (GSE) data model."""

    ID: Optional[float] = None
    title: Optional[str] = None
    gse: Optional[str] = None
    status: Optional[str] = None
    submission_date: Optional[str] = None
    last_update_date: Optional[str] = None
    pubmed_id: Optional[int] = None
    summary: Optional[str] = None
    type: Optional[str] = None
    contributor: Optional[str] = None
    web_link: Optional[str] = None
    overall_design: Optional[str] = None
    repeats: Optional[str] = None
    repeats_sample_list: Optional[str] = None
    variable: Optional[str] = None
    variable_description: Optional[str] = None
    contact: Optional[str] = None
    supplementary_file: Optional[str] = None
