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

    def __eq__(self, other: 'GSE') -> bool:
        return self.gse == other.gse and self.title == other.title and self.status == other.status and self.submission_date == other.submission_date and self.last_update_date == other.last_update_date and self.pubmed_id == other.pubmed_id and self.summary == other.summary and self.type == other.type and self.contributor == other.contributor and self.web_link == other.web_link and self.overall_design == other.overall_design and self.repeats == other.repeats and self.repeats_sample_list == other.repeats_sample_list and self.variable == other.variable and self.variable_description == other.variable_description and self.contact == other.contact and self.supplementary_file == other.supplementary_file
    
    def to_dict(self) -> dict:
        return {
            "gse": self.gse,
            "title": self.title,
            "status": self.status,
            "submission_date": self.submission_date,
            "last_update_date": self.last_update_date,
            "pubmed_id": self.pubmed_id,
            "summary": self.summary,
            "type": self.type,
            "contributor": self.contributor,
            "web_link": self.web_link,
            "overall_design": self.overall_design,
            "repeats": self.repeats,
            "repeats_sample_list": self.repeats_sample_list,
            "variable": self.variable,
            "variable_description": self.variable_description,
            "contact": self.contact,
            "supplementary_file": self.supplementary_file,
        }
    
    def from_dict(self, data: dict) -> 'GSE':
        return GSE(
            gse=data["gse"],
            title=data["title"],
            status=data["status"],
            submission_date=data["submission_date"],
            last_update_date=data["last_update_date"],
            pubmed_id=data["pubmed_id"],
            summary=data["summary"],
            type=data["type"],
            contributor=data["contributor"],
            web_link=data["web_link"],
            overall_design=data["overall_design"],
            repeats=data["repeats"],
            repeats_sample_list=data["repeats_sample_list"],
            variable=data["variable"],
            variable_description=data["variable_description"],
            contact=data["contact"],
            supplementary_file=data["supplementary_file"],
        )