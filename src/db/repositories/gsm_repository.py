import logging
import os
from typing import List, Dict

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.db.loaders.gsm_loader import GSMLoader
from src.db.models import GSE_GSM
from src.db.models.gsm import GSM
from src.db.repositories.is_disk_full_db_error import handle_disk_space_error
from src.db.repositories.sqlalchemy_engine_helpers import create_sync_engine

logger = logging.getLogger(__name__)


class GSMRepository(GSMLoader):
    def __init__(self, geometadb_path: str) -> None:
        if not os.path.isfile(geometadb_path):
            raise RuntimeError(f"Geometadb file {geometadb_path} does not exist")
        if not os.access(geometadb_path, os.W_OK):
            raise RuntimeError(f"Geometadb file {geometadb_path} is not writable")
        self.engine = create_sync_engine(geometadb_path)
        self.geometadb_path = geometadb_path

    @handle_disk_space_error
    def save_gsms(self, gsms: List[GSM]) -> None:
        """
        Saves GEO samples to the geometadb sqlite database.

        :param gsms: List of GEO samples to save.
        """
        if not gsms:
            return
        gse_gsm_links = [GSE_GSM(gse=gsm.series_id, gsm=gsm.gsm) for gsm in gsms]
        try:
            with Session(self.engine) as session:
                for gsm in gsms:
                    session.merge(gsm)
                for gse_gsm_link in gse_gsm_links:
                    session.merge(gse_gsm_link)
                session.commit()
        except SQLAlchemyError:
            logger.exception("Failed to save GEO samples to geometadb:")
            raise

    def get_gsms(self, gsm_accessions: List[str]) -> List[GSM]:
        """
        Loads GEO samples from the geometadb sqlite database.

        :param gsm_accessions: List of GEO accessions for the samples.
        :return: List of GEO samples
        """
        if not gsm_accessions:
            return []
        try:
            with Session(self.engine) as session:
                statement = select(GSM).where(GSM.gsm.in_(gsm_accessions))
                return list(session.scalars(statement).all())
        except SQLAlchemyError as e:
            logger.exception("Failed to load GEO samples from geometadb:")
            raise e

    def get_gse_gsm_mapping(self, gse_accesions: List[str]) -> Dict[str, List[GSM]]:
        """
        Returns a mapping of GSE accessions to their associated GSM samples.
        """
        if not gse_accesions:
            return {}

        try:
            with Session(self.engine) as session:
                statement_gse_gsm_map = select(GSE_GSM).where(GSE_GSM.gse.in_(gse_accesions))
                gse_gsm_map = {}
                for gse_gsm in session.scalars(statement_gse_gsm_map).all():
                    gse_gsm_map.setdefault(gse_gsm.gse, []).append(gse_gsm.gsm)

                statement_gsms = select(GSM).join(GSE_GSM).where(GSE_GSM.gse.in_(gse_accesions))
                gsms = {gsm.gsm: gsm for gsm in session.scalars(statement_gsms).all()}

                for gse_acc in gse_gsm_map:
                    gse_gsm_map[gse_acc] = [gsms[gsm_acc] for gsm_acc in gse_gsm_map[gse_acc]]

                return gse_gsm_map

        except SQLAlchemyError as e:
            logger.exception("Failed to load GEO samples from geometadb:")
            raise e
