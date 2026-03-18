from typing import Dict
from GEOparse import GSE
import logging

GEOMETADB_SEPARATOR = ";\t"
logger = logging.getLogger(__name__)


def get_geometadb_dict(geoparse_gse: GSE) -> Dict:
    return format_geoparse_gse_metadata(geoparse_gse.metadata)


def format_geoparse_gse_metadata(gse_metadata: Dict) -> Dict:
    """
    Formats the metadata dictionary from GEOparse into a format suitable for
    creating a GSE object.

    :param gse_metadata: Metadata dictionary from GEOparse.
    """
    metadata_dict = {key: item[0] if isinstance(item, list) and len(item) > 0 else "" for key, item in
                     gse_metadata.items()}
    metadata_dict["gse"] = metadata_dict.get("geo_accession", "")
    if "pubmed_id" in metadata_dict:
        try:
            metadata_dict["pubmed_id"] = int(metadata_dict["pubmed_id"])
        except ValueError:
            logger.warning(f"Invalid PubMed ID: {metadata_dict['pubmed_id']}")
            metadata_dict["pubmed_id"] = None
    format_contact_info(metadata_dict)
    if "contributor" in gse_metadata:
        metadata_dict["contributor"] = GEOMETADB_SEPARATOR.join(gse_metadata["contributor"])
    return metadata_dict


def format_geoparse_gsm_metadata(gsm_metadata: Dict) -> Dict:
    """
    Formats the metadata dictionary from GEOparse into a format suitable for
    creating a GSE object.

    :param gsm_metadata: Metadata dictionary from GEOparse.
    """
    metadata_dict = {key: item[0] if isinstance(item, list) and len(item) > 0 else "" for key, item in
                     gsm_metadata.items()}
    metadata_dict["gsm"] = metadata_dict.get("geo_accession", "")
    metadata_dict["channel_count"] = float(metadata_dict.get("channel_count", 0))
    metadata_dict["data_row_count"] = float(metadata_dict.get("data_row_count", 0))
    format_contact_info(metadata_dict)
    if "contributor" in gsm_metadata:
        metadata_dict["contributor"] = GEOMETADB_SEPARATOR.join(gsm_metadata["contributor"])
    return metadata_dict


def format_contact_info(metadata_dict):
    """
    Formats the contact information from GEOparse into a single string
    in the format used in geometadb.
    Adds a contact field to the metadata dictionary with the formatted
    contact info.

    :param metadata_dict: Metadata dictionary from GEOparse.
    """
    contact_info = []
    if "contact_name" in metadata_dict:
        contact_info.append(f'Name: {metadata_dict["contact_name"]}')
    if "contact_email" in metadata_dict:
        contact_info.append(f'Email: {metadata_dict["contact_email"]}')
    if "contact_department" in metadata_dict:
        contact_info.append(f'Department: {metadata_dict["contact_department"]}')
    if "contact_laboratory" in metadata_dict:
        contact_info.append(f'Laboratory: {metadata_dict["contact_laboratory"]}')
    if "contact_institute" in metadata_dict:
        contact_info.append(f'Institute: {metadata_dict["contact_institute"]}')
    if "contact_city" in metadata_dict:
        contact_info.append(f'City: {metadata_dict["contact_city"]}')
    if "contact_zip/postal_code" in metadata_dict:
        contact_info.append(f'Zip/Postal Code: {metadata_dict["contact_zip/postal_code"]}')
    if "contact_country" in metadata_dict:
        contact_info.append(f'Country: {metadata_dict["contact_country"]}')
    if "contact_phone" in metadata_dict:
        contact_info.append(f'Phone: {metadata_dict["contact_phone"]}')
    metadata_dict["contact"] = GEOMETADB_SEPARATOR.join(contact_info)
