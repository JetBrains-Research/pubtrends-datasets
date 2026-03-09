import logging
from typing import List, Iterable

import numpy as np
import spacy

from src.config.config import Config
from src.db.gse import GSE
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

    def chunk_gse(self, gse: GSE) -> List[str]:
        chunks = [gse.title]
        if gse.is_superseries():
            return chunks
        if gse.summary:
            chunks.extend(get_chunks(gse.summary, self.max_tokens_per_chunk, self.overlap_sentences))
        if gse.overall_design:
            chunks.extend(get_chunks(gse.overall_design, self.max_tokens_per_chunk, self.overlap_sentences))
        return chunks


    def embed_gses(self, gses: List[GSE]) -> list[tuple[np.ndarray, GSE]]:
        chunks_with_gse = [(chunk, gse) for gse in gses for chunk in self.chunk_gse(gse)]

        chunks = [chunk for chunk, _ in chunks_with_gse]
        embeddings = fetch_texts_embedding(chunks, self.embeddings_service_url)

        result = [(embedding, gse) for embedding, (_, gse) in zip(embeddings, chunks_with_gse)]

        return result


    def rank_by_relevance(self, gses: List[GSE], query: str) -> List[ScoredGSE]:
        if len(gses) == 0:
            return []
        query_embedding = fetch_texts_embedding([query], self.embeddings_service_url)[0]

        embeddings_with_gse = self.embed_gses(gses)
        embeddings = np.array([embedding for embedding, _ in embeddings_with_gse])
        scores = cosine_similarity(query_embedding, embeddings)
        gses_with_scores = [(embeddings_with_gse[i][1], scores[i]) for i in range(len(embeddings_with_gse))]

        ranked_gses_with_scores = sorted(gses_with_scores, key=lambda x: x[1], reverse=True)
        return stable_deduplicate([ScoredGSE(*entry) for entry in ranked_gses_with_scores], lambda x: x.gse.gse)
