import logging
from typing import Iterable

import spacy

from src.db.gse import GSE
from src.semantic_search.embeddings_service import fetch_texts_embedding
from src.semantic_search.faiss_connector import FaissConnector

logger = logging.getLogger(__name__)


class GSEIndexer:
    def __init__(self, faiss_connector: FaissConnector):
        self.faiss_connector = faiss_connector

    def store_in_index(self, gses: Iterable[GSE]):
        index = [(chunk, gse.gse) for gse in gses for chunk in self.chunk(gse)]
        embeddings = fetch_texts_embedding([entry[0] for entry in index])
        self.faiss_connector.store_embeddings(index, embeddings)
        self.faiss_connector.save()

