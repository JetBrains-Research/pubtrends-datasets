import logging
from collections import defaultdict
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

def is_float(string_val):
    try:
        float(string_val)
        return True
    except ValueError:
        return False
    except TypeError: # Handles cases like None
        return False

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

    def chunk_gse(self, gse: GSE, gsms: List[GSM]) -> List[str]:
        chunks = [gse.title]
        if gse.is_superseries():
            return chunks
        if gse.summary:
            chunks.extend(get_chunks(gse.summary, self.max_tokens_per_chunk, self.overlap_sentences))
        if gse.overall_design:
            chunks.extend(get_chunks(gse.overall_design, self.max_tokens_per_chunk, self.overlap_sentences))
        if gsms:
            sample_summary_chunks = get_chunks(
                self.get_sample_summary(gsms),
                self.max_tokens_per_chunk,
                self.overlap_sentences,
            )
            chunks.extend(sample_summary_chunks)
        return chunks

    @staticmethod
    def is_all_numeric(values: str):
        return  all(value.isnumeric() for value in values)

    @staticmethod
    def get_characteristics_summary(gsms: List[GSM]) -> str:
        characteristics = defaultdict(list)
        for gsm in gsms:
            for characteristic, value in gsm.characteristics.items():
                characteristics[characteristic].append(value)
        sample_characteristics_summary = "Sample characteristics summary: \n"
        for characteristic, values in characteristics.items():
            if all(is_float(value) for value in values):
                sample_characteristics_summary += f"{characteristic} range: {min(values)}-{max(values)};\n"
            else:
                values = list(set(values))
                sample_characteristics_summary += f"{characteristic}: {', '.join(values[:10])};\n"


        return sample_characteristics_summary

    @staticmethod
    def get_sample_summary(gsms: List[GSM]) -> str:
        sample_summary = "Study sample summary\n"
        organisms = {gsm.organism_ch1 for gsm in gsms}
        sample_summary += f"{'Organism' if len(organisms) == 1 else 'Organisms'}: {', '.join(organisms)}\n"
        sample_summary += f"Molecule: {gsms[0].molecule_ch1}\n"
        sample_summary += SemanticSearcher.get_characteristics_summary(gsms)
        return sample_summary

    def embed_gses(self, gses: List[GSE], gsms_for_gse: Dict[str, List[GSM]]) -> list[tuple[np.ndarray, GSE]]:
        chunks_with_gse = [(chunk, gse) for gse in gses for chunk in self.chunk_gse(gse, gsms_for_gse[gse.gse])]

        chunks = [chunk for chunk, _ in chunks_with_gse]
        embeddings = fetch_texts_embedding(chunks, self.embeddings_service_url)

        result = [(embedding, gse) for embedding, (_, gse) in zip(embeddings, chunks_with_gse)]

        return result

    def rank_by_relevance(self, gses: List[GSE], gsms_for_gse: Dict[str, List[GSM]], query: str) -> List[ScoredGSE]:
        if len(gses) == 0:
            return []
        query_embedding = fetch_texts_embedding([query], self.embeddings_service_url)[0]

        embeddings_with_gse = self.embed_gses(gses, gsms_for_gse)
        embeddings = np.array([embedding for embedding, _ in embeddings_with_gse])
        scores = cosine_similarity(query_embedding, embeddings)
        scored_gses = [ScoredGSE(GSE_DTO(embeddings_with_gse[i][1]), scores[i]) for i in range(len(embeddings_with_gse))]

        ranked_scored_gses = list(sorted(scored_gses, key=lambda x: x.score, reverse=True))
        return stable_deduplicate(ranked_scored_gses, lambda x: x.gse.gse)
