import logging
from typing import List

import GEOparse
import requests
from dacite import from_dict

from src.db.loaders.geoparse_to_geometadb import format_geoparse_gsm_metadata
from src.db.loaders.gsm_loader import GSMLoader
from src.db.models.gsm import GSM
from src.db.repositories.gsm_repository import GSMRepository
from src.exception.geo_error import GEOError

logger = logging.getLogger(__name__)


class NCBIGSMLoader(GSMLoader):
    DOWNLOAD_URL_TEMPLATE = "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={}&targ=self&form=text&view=quick"

    def __init__(self, session: requests.Session, repository: GSMRepository) -> None:
        self.session = session
        self.repository = repository

    def get_gsms(self, gsm_accessions: List[str]) -> List[GSM]:
        gsms = [self.download_geo_sample(accession) for accession in gsm_accessions]
        self.repository.save_gsms(gsms)
        return gsms

    def download_geo_sample(self, accession: str) -> GSM:
        """
        Downloads the GEO sample with the given accession.

        :param accession: GEO accession for the sample (ex. GSM123456)
        :return: GEO sample
        """
        sample_metadata_url = NCBIGSMLoader.DOWNLOAD_URL_TEMPLATE.format(accession)
        try:
            logger.info(f"Downloading GEO sample {accession}")
            response = self.session.get(sample_metadata_url, stream=True)
            response.raise_for_status()
            metadata = GEOparse.GEOparse.parse_metadata(response.iter_lines(decode_unicode=True))
            formatted_metadata = format_geoparse_gsm_metadata(metadata)
            return from_dict(GSM, formatted_metadata)
        except requests.HTTPError as e:
            raise GEOError(f"Error downloading GEO sample {accession}: {e.response.status_code}")
        except requests.RequestException:
            raise GEOError(f"Network failure when downloading GEO sample {accession}")
