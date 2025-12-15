import logging
import sqlite3
from dataclasses import fields, astuple
from typing import List, Dict

import GEOparse
import requests
from dacite import from_dict

from src.config.config import Config
from src.db.gse import GSE
from src.db.gse_loader import GSELoader
from src.exception.geo_error import GEOError

logger = logging.getLogger(__name__)

class NCBIGSELoader(GSELoader):
    DOWNLOAD_URL_TEMPLATE = "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={}&targ=self&form=text&view=quick"
    GEOMETADB_SEPARATOR = ";\t"
    def __init__(self, session: requests.Session, config: Config) -> None:
        self.session = session
        self.geometadb_path = config.geometadb_path

    def load_gses(self, gse_accessions: List[str]) -> List[GSE]:
        gses = [self.download_geo_dataset(accession) for accession in gse_accessions]
        self.save_gses(gses)
        return gses

    def save_gses(self, gses: list[GSE]):
        try:
            with sqlite3.connect(self.geometadb_path) as conn:
                cursor = conn.cursor()
                field_names = [f.name for f in fields(GSE)]
                headers = ','.join(field_names)
                gse_tuples = [astuple(gse) for gse in gses]
                placeholders = ','.join(['?'] * len(field_names))
                table = 'gse'
                cursor.executemany(f"INSERT OR REPLACE INTO {table} ({headers}) VALUES ({placeholders})", gse_tuples)
        except sqlite3.Error:
            # Just log the exception so as not to fail the whole pipeline.
            logger.exception("Failed to save GEO datasets to geometadb:")

    @staticmethod
    def _format_geoparse_metadata(geoparse_metadata: Dict):
        metadata_dict = {key: item[0] if isinstance(item, list) and len(item) > 0 else "" for key, item in geoparse_metadata.items()}
        metadata_dict["gse"] = metadata_dict.get("geo_accession", "")
        if "pubmed_id" in metadata_dict:
            metadata_dict["pubmed_id"] = int(metadata_dict["pubmed_id"])
        NCBIGSELoader._format_contact_info(metadata_dict)
        if "contributor" in geoparse_metadata:
            metadata_dict["contributor"] = NCBIGSELoader.GEOMETADB_SEPARATOR.join(geoparse_metadata["contributor"])
        return metadata_dict

    @staticmethod
    def _format_contact_info(metadata_dict):
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
        metadata_dict["contact"] = NCBIGSELoader.GEOMETADB_SEPARATOR.join(contact_info)

    def download_geo_dataset(self, accession: str) -> GSE:
        """
        Downloads the GEO dataset with the given accession.

        :param accession: GEO accession for the dataset (ex. GSE12345)
        :return: GEO dataset
        """
        dataset_metadata_url = NCBIGSELoader.DOWNLOAD_URL_TEMPLATE.format(accession)
        try:
            response = self.session.get(dataset_metadata_url, stream=True)
            response.raise_for_status()
            metadata = GEOparse.GEOparse.parse_metadata(response.iter_lines(decode_unicode=True))
            return from_dict(GSE, NCBIGSELoader._format_geoparse_metadata(metadata))
        except requests.HTTPError as e:
            raise GEOError(f"Error downloading GEO dataset {accession}: {e.response.status_code}")
        except requests.RequestException:
            raise GEOError(f"Network failure when downloading GEO dataset {accession}")
