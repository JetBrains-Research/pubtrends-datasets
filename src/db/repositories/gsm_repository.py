import logging
import os
from typing import List, Dict

from sqlalchemy import create_engine, event, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.db.models import GSE_GSM
from src.db.models.gsm import GSM
from src.db.loaders.gsm_loader import GSMLoader

logger = logging.getLogger(__name__)


class GSMRepository(GSMLoader):
    def __init__(self, geometadb_path: str) -> None:
        if not os.path.isfile(geometadb_path):
            raise RuntimeError(f"Geometadb file {geometadb_path} does not exist")
        if not os.access(geometadb_path, os.W_OK):
            raise RuntimeError(f"Geometadb file {geometadb_path} is not writable")
        self.engine = create_engine(f"sqlite:///{geometadb_path}")
        self.geometadb_path = geometadb_path

        @event.listens_for(self.engine, "connect")
        def set_sqlite_text_factory(dbapi_connection, connection_record):
            dbapi_connection.text_factory = lambda x: x.decode(errors="replace")

    def save_gsms(self, gsms: List[GSM]) -> None:
        """
        Saves GEO samples to the geometadb sqlite database.

        :param gsms: List of GEO samples to save.
        """
        if not gsms:
            return
        try:
            with Session(self.engine) as session:
                for gsm in gsms:
                    session.merge(gsm)
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

    def get_gsms_for_gse(self, gse_accesions: List[str]) -> Dict[str, List[GSM]]:
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
