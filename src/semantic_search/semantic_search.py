import concurrent
import logging
import time
from typing import List, Iterable, Dict

import numpy as np
import spacy

from src.config.config import Config
from src.db.models import GSM
from src.db.models.gse import GSE, GSE_DTO
from src.semantic_search.embeddings_service import fetch_texts_embedding
from src.semantic_search.scored_gse import ScoredGSE

logger = logging.getLogger(__name__)

NLP = spacy.load("en_core_web_sm")


def cosine_similarity(vector, matrix):
    vector_norm = np.linalg.norm(vector)
    matrix_norms = np.linalg.norm(matrix, axis=1)
    if vector_norm == 0:
        return np.zeros(matrix.shape[0])
    safe_norms = np.where(matrix_norms == 0, 1.0, matrix_norms)
    return (matrix @ vector) / (safe_norms * vector_norm)


def stable_deduplicate(iterable: Iterable, key_fn):
    added = set()
    return [x for x in iterable if not (key_fn(x) in added or added.add(key_fn(x)))]


def get_chunks(text, max_tokens_per_chunk=128, overlap_sentences=1):
    """
    Split text into a list of overlapping chunks.

    Args:
        text (str): The text to split into chunks
        max_tokens_per_chunk (int): Maximum number of tokens per chunk
        overlap_sentences (int): Number of sentences to overlap between chunks

    Returns:
        list: List of text chunks
    """

    # Only select necessary pipeline components to speed up processing
    with NLP.select_pipes(enable=['tok2vec', "parser", "senter"]):
        # Get all sentences
        sentences = list(NLP(text).sents)

    if not sentences:
        return [text]

    chunks = []
    current_chunk_sentences = []
    current_token_count = 0

    for sentence in sentences:
        # If adding this sentence exceeds max_tokens, create a new chunk
        if current_token_count + len(sentence) > max_tokens_per_chunk and current_chunk_sentences:
            # Join the sentences in the current chunk
            chunk_text = ' '.join([s.text for s in current_chunk_sentences])
            chunks.append(chunk_text)

            # Keep the overlapping sentences for the next chunk
            if overlap_sentences > 0:
                overlap_size = min(overlap_sentences, len(current_chunk_sentences))
                current_chunk_sentences = current_chunk_sentences[-overlap_size:]
                current_token_count = sum(len(s) for s in current_chunk_sentences)
            else:
                current_chunk_sentences = []
                current_token_count = 0

        # Add the current sentence to the chunk
        current_chunk_sentences.append(sentence)
        current_token_count += len(sentence)

    # Add the last chunk if there are any sentences left
    if current_chunk_sentences:
        chunk_text = ' '.join([s.text for s in current_chunk_sentences])
        chunks.append(chunk_text)
    return chunks


class SemanticSearcher:
    def __init__(self, config: Config):
        self.max_tokens_per_chunk = config.max_tokens_per_chunk
        self.overlap_sentences = config.overlap_sentences
        self.embeddings_service_url = config.embeddings_service_url
        self.chunking_workers = config.chunking_workers

    def chunk_gse(self, gse: GSE, gsms: List[GSM]) -> List[str]:
        chunks = [gse.title]
        if gse.is_superseries():
            return chunks
        if gse.summary:
            chunks.extend(get_chunks(gse.summary, self.max_tokens_per_chunk, self.overlap_sentences))
        if gse.overall_design:
            chunks.extend(get_chunks(gse.overall_design, self.max_tokens_per_chunk, self.overlap_sentences))
        if gsms:
            chunks.extend(
                chunk for gsm in gsms for chunk in get_chunks(str(gsm))
            )
        return chunks

    def embed_gses(self, gses: List[GSE], gsms_for_gse: Dict[str, List[GSM]]) -> list[tuple[np.ndarray, GSE]]:
        start = time.perf_counter()
        with concurrent.futures.ProcessPoolExecutor(max_workers=self.chunking_workers) as executor:
            chunks_for_gses = list(executor.map(self.chunk_gse, gses, (gsms_for_gse[gse.gse] for gse in gses)))
            chunks_with_gse = [(chunk, gse) for chunks, gse in zip(chunks_for_gses, gses) for chunk in chunks]
        end = time.perf_counter()
        chunk_count = len(chunks_with_gse)

        number_of_gsms = sum(len(gsms) for gsms in gsms_for_gse.values())
        logger.info(
            f"Chunks created in {end - start} seconds for {len(gses)} GSEs and {chunk_count} chunks and {number_of_gsms} GSMs")

        embedding_start_time = time.perf_counter()
        embeddings = fetch_texts_embedding([chunk for chunk, _ in chunks_with_gse], self.embeddings_service_url)
        embedding_end_time = time.perf_counter()
        logger.info(
            f"Embeddings fetched in {embedding_end_time - embedding_start_time} seconds for {chunk_count} chunks")

        return [(embedding, gse) for embedding, (_, gse) in zip(embeddings, chunks_with_gse)]

    def rank_by_relevance(self, gses: List[GSE], gsms_for_gse: Dict[str, List[GSM]], query: str) -> List[ScoredGSE]:
        if not gses:
            return []
        query_embedding = fetch_texts_embedding([query], self.embeddings_service_url)[0]

        embeddings_with_gse = self.embed_gses(gses, gsms_for_gse)
        embeddings = np.array([embedding for embedding, _ in embeddings_with_gse])
        scores = cosine_similarity(query_embedding, embeddings)
        scored_gses = [
            ScoredGSE(GSE_DTO(gse), score)
            for (_, gse), score in zip(embeddings_with_gse, scores)
        ]

        ranked_scored_gses = sorted(scored_gses, key=lambda x: x.score, reverse=True)
        return stable_deduplicate(ranked_scored_gses, lambda x: x.gse.gse)
