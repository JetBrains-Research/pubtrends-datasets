"""Gene Expression Omnibus Sample (GSM) data model."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class GSM:
    """Gene Expression Omnibus Sample (GSM) data model."""
    
    ID: Optional[float] = None
    title: Optional[str] = None
    gsm: Optional[str] = None
    series_id: Optional[str] = None
    gpl: Optional[str] = None
    status: Optional[str] = None
    submission_date: Optional[str] = None
    last_update_date: Optional[str] = None
    type: Optional[str] = None
    source_name_ch1: Optional[str] = None
    organism_ch1: Optional[str] = None
    characteristics_ch1: Optional[str] = None
    molecule_ch1: Optional[str] = None
    label_ch1: Optional[str] = None
    treatment_protocol_ch1: Optional[str] = None
    extract_protocol_ch1: Optional[str] = None
    label_protocol_ch1: Optional[str] = None
    source_name_ch2: Optional[str] = None
    organism_ch2: Optional[str] = None
    characteristics_ch2: Optional[str] = None
    molecule_ch2: Optional[str] = None
    label_ch2: Optional[str] = None
    treatment_protocol_ch2: Optional[str] = None
    extract_protocol_ch2: Optional[str] = None
    label_protocol_ch2: Optional[str] = None
    hyb_protocol: Optional[str] = None
    description: Optional[str] = None
    data_processing: Optional[str] = None
    contact: Optional[str] = None
    supplementary_file: Optional[str] = None
    data_row_count: Optional[float] = None
    channel_count: Optional[float] = None

