import logging
from functools import cache
from typing import List, Iterable

import numpy as np

from src.config.config import Config
from src.db.gse import GSE
from src.semantic_search.faiss_connector import FaissConnector
from src.semantic_search.embeddings_service import fetch_texts_embedding
from src.semantic_search.gse_indexer import GSEIndexer

logger = logging.getLogger(__name__)

def l2norm(v):
    norm = np.linalg.norm(v)
    if norm == 0:
        norm = np.finfo(v.dtype).eps
    v /= norm
    return v

def stable_deduplicate(iterable):
    return list(dict.fromkeys(iterable))

def semantic_search_faiss_embedding(faiss_index, gses_idx, query_embedding, k):
    # Normalize embeddings if using cosine similarity
    query_embedding = l2norm(query_embedding)

    # Validate embedding dimension matches FAISS index
    expected_dim = faiss_index.d
    actual_dim = query_embedding.shape[1]
    if actual_dim != expected_dim:
        raise ValueError(
            f"Embedding dimension mismatch: query embedding has dimension {actual_dim}, "
            f"but FAISS index expects dimension {expected_dim}. "
            f"Query embedding shape: {query_embedding.shape}"
        )

    similarities, indices = faiss_index.search(query_embedding.astype('float32'), k)
    t = gses_idx.iloc[indices[0]].copy().reset_index(drop=True)
    t['similarity'] = similarities[0]
    # Workaround for correct gse_ids index table
    return t[['gse_acc', 'chunk', 'similarity']]

class SemanticSearch():
    def __init__(self, config: Config):
        self.faiss_connector = FaissConnector("geo", config.sentence_transformer_model, config.embeddings_dimension)
        self.indexer = GSEIndexer(self.faiss_connector)

    def rank_by_relevance(self, gses: Iterable[GSE], query: str) -> List[GSE]:
        faiss_index = self.faiss_connector.faiss_index
        for gse in gses:
            if not self.is_gse_in_index(gse.gse):
                self.indexer.store_in_index(gse)

        gse_accs = [gse.gse for gse in gses]
        k = faiss_index.ntotal
        result = self._search_raw(query, k)
        result_accs = result['gse_acc'].tolist()
        gse_id_set = set(gse_accs)
        ranked_gse_accs = stable_deduplicate([gse_acc for gse_acc in result_accs if gse_acc in gse_id_set])

        gse_dict = {gse.gse: gse for gse in gses}
        return [gse_dict[gse_acc] for gse_acc in ranked_gse_accs]



    def _search_raw(self, text, n):
        embeddings_func = lambda t: fetch_texts_embedding([t])[0]
        query_embedding = embeddings_func(text).reshape(1, -1)
        faiss_index, gses_idx = self.faiss_connector.faiss_index, self.faiss_connector.gse_acc_idx
        result = semantic_search_faiss_embedding(faiss_index, gses_idx, query_embedding, n)
        return result

    def is_gse_in_index(self, gse_acc):
        return self.faiss_connector.is_gse_in_index(gse_acc)
