import logging
from typing import List

import GEOparse
import requests
import tenacity
from dacite import from_dict

from src.db.loaders.geoparse_to_geometadb import format_geoparse_gse_metadata
from src.db.models.gse import GSE
from src.db.loaders.gse_loader import GSELoader
from src.db.repositories.gse_repository import GSERepository
from src.exception.geo_error import GEOError

logger = logging.getLogger(__name__)


class NCBIGSELoader(GSELoader):
    DOWNLOAD_URL_TEMPLATE = "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={}&targ=self&form=text&view=quick"

    def __init__(self, session: requests.Session, repository: GSERepository) -> None:
        self.session = session
        self.repository = repository

    def get_gses(self, gse_accessions: List[str]) -> List[GSE]:
        gses = [self.download_geo_dataset(accession) for accession in gse_accessions]
        self.repository.save_gses(gses)
        return gses

    @tenacity.retry(wait=tenacity.wait_exponential(max=10), stop=tenacity.stop_after_attempt(3), before_sleep=tenacity.before_sleep_log(logger, logging.WARNING), reraise=True)
    def download_geo_dataset(self, accession: str) -> GSE:
        """
        Downloads the GEO dataset with the given accession.

        :param accession: GEO accession for the dataset (ex. GSE12345)
        :return: GEO dataset
        """
        dataset_metadata_url = NCBIGSELoader.DOWNLOAD_URL_TEMPLATE.format(accession)
        try:
            logger.info(f"Downloading GEO dataset {accession}")
            response = self.session.get(dataset_metadata_url, stream=True)
            response.raise_for_status()
            metadata = GEOparse.GEOparse.parse_metadata(response.iter_lines(decode_unicode=True))
            return from_dict(GSE, format_geoparse_gse_metadata(metadata))
        except requests.HTTPError as e:
            raise GEOError(f"Error downloading GEO dataset {accession}: {e.response.status_code}")
        except requests.RequestException:
            raise GEOError(f"Network failure when downloading GEO dataset {accession}")
