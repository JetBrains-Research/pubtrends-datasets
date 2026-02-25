import logging
from typing import List, Iterable

import numpy as np
import spacy

from src.db.gse import GSE
from src.semantic_search.embeddings_service import fetch_texts_embedding

logger = logging.getLogger(__name__)

NLP = spacy.load("en_core_web_sm")


def cosine_similarity(vector, matrix):
    vector_norm = np.linalg.norm(vector)
    matrix_norms = np.linalg.norm(matrix, axis=1)
    if vector_norm == 0:
        return np.zeros(matrix.shape[0])
    safe_norms = np.where(matrix_norms == 0, 1.0, matrix_norms)
    return (matrix @ vector) / (safe_norms * vector_norm)


def stable_deduplicate_gses(iterable: Iterable[GSE]):
    added = set()
    return [x for x in iterable if not (x.gse in added or added.add(x.gse))]


def get_chunks(text, max_tokens=128, overlap_sentences=1):
    """
    Split text into a list of overlapping chunks.

    Args:
        text (str): The text to split into chunks
        max_tokens (int): Maximum number of tokens per chunk
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
        if current_token_count + len(sentence) > max_tokens and current_chunk_sentences:
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


def chunk_gse(gse: GSE) -> List[str]:
    chunks = [gse.title]
    if not gse.is_superseries():
        chunks.extend(get_chunks(gse.summary))
        chunks.extend(get_chunks(gse.overall_design))
    return chunks


def embed_gses(gses: List[GSE]) -> list[tuple[np.ndarray, GSE]]:
    chunks_with_gse = [(chunk, gse) for gse in gses for chunk in chunk_gse(gse)]

    chunks = [chunk for chunk, _ in chunks_with_gse]
    embeddings = fetch_texts_embedding(chunks)

    result = [(embedding, gse) for embedding, (_, gse) in zip(embeddings, chunks_with_gse)]

    return result


def rank_by_relevance(gses: List[GSE], query: str) -> List[GSE]:
    query_embedding = fetch_texts_embedding([query])[0]

    embeddings_with_gse = embed_gses(gses)
    embeddings = np.array([embedding for embedding, _ in embeddings_with_gse])
    scores = cosine_similarity(query_embedding, embeddings)

    gses_with_scores = list(zip(gses, scores))
    ranked_gses_with_scores = sorted(gses_with_scores, key=lambda x: x[1], reverse=True)
    ranked_gses = [entry[0] for entry in ranked_gses_with_scores]
    return stable_deduplicate_gses(ranked_gses)
