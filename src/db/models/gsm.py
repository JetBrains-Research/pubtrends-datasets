"""Gene Expression Omnibus Sample (GSM) data model."""
from dataclasses import dataclass, field
from typing import Optional, List, Dict

from sqlalchemy import Column, Index, PrimaryKeyConstraint, REAL, Text

from src.db.models.mapper_registry import mapper_registry


@mapper_registry.mapped
@dataclass
class GSM:
    """Gene Expression Omnibus Sample (GSM) data model."""
    __tablename__ = 'gsm'
    __table_args__ = (
        PrimaryKeyConstraint('gsm', name='pk_gsm'),
        Index('gsm_acc_idx', 'gsm')
    )
    __sa_dataclass_metadata_key__ = "sa"

    gsm: str = field(metadata={"sa": Column(Text, primary_key=True)})
    ID: Optional[float] = field(default=None, metadata={"sa": Column(REAL)})
    title: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    series_id: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    gpl: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    status: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    submission_date: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    last_update_date: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    type: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    source_name_ch1: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    organism_ch1: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    characteristics_ch1: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    molecule_ch1: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    label_ch1: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    treatment_protocol_ch1: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    extract_protocol_ch1: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    label_protocol_ch1: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    source_name_ch2: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    organism_ch2: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    characteristics_ch2: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    molecule_ch2: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    label_ch2: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    treatment_protocol_ch2: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    extract_protocol_ch2: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    label_protocol_ch2: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    hyb_protocol: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    description: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    data_processing: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    contact: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    supplementary_file: Optional[str] = field(default=None, metadata={"sa": Column(Text)})
    data_row_count: Optional[float] = field(default=None, metadata={"sa": Column(REAL)})
    channel_count: Optional[float] = field(default=None, metadata={"sa": Column(REAL)})

    def __str__(self):
        lines = [f"Sample: {self.title}"]
        if self.source_name_ch1:
            lines.append(f"Source: {self.source_name_ch1}")
        if self.organism_ch1:
            lines.append(f"Organism: {self.organism_ch1}")
        if self.molecule_ch1:
            lines.append(f"Molecule: {self.molecule_ch1}")
        if self.characteristics_ch1:
            lines.append(f"Characteristics:")
            for characteristic, value in _parse_characteristics(self.characteristics_ch1.split(";")).items():
                lines.append(f"{characteristic}: {value}")

        return "\n".join(lines)


def _parse_characteristics(characteristics: List[str]) -> Dict[str, str]:
    """
    Parses the characterstics key value pairs and stores them in a
    dictionary.
    :param characteristics: Sample characterestics extracted from the
    metadata from a sample.
    :return: Dictionary where the keys are the names of the characteristics.
    """
    if characteristics is None:
        return {}
    characteristics_dict = {}
    for characteristic in characteristics:
        try:
            key, value = characteristic.strip().split(":", 1)
            characteristics_dict[key.lower()] = value.strip().lower()
        except ValueError:
            unparsed_key = "unparsed_characteristics"
            current_unparsed = characteristics_dict.get(unparsed_key, "")
            characteristics_dict[unparsed_key] = current_unparsed + \
                                                 "|" + characteristic
    return characteristics_dict


@property
def characteristics(self):
    return self._parse_characteristics(self.characteristics_ch1.split(";") if self.characteristics_ch1 else [])
