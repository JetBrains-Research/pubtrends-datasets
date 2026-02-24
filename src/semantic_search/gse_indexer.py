import logging

import spacy

from src.db.gse import GSE
from src.semantic_search.embeddings_service import fetch_texts_embedding
from src.semantic_search.faiss_connector import FaissConnector

NLP = spacy.load("en_core_web_sm")
SUPERSERIES_SUMMARY = "This SuperSeries is composed of the SubSeries listed below."
logger = logging.getLogger(__name__)

class GSEIndexer:
    def __init__(self, faiss_connector: FaissConnector):
        self.faiss_connector = faiss_connector

    @staticmethod
    def is_superseries(gse: GSE):
        return gse.summary == SUPERSERIES_SUMMARY

    def store_in_index(self, gse: GSE):
        logger.info(f'Indexing GSE {gse.gse}')
        chunks, gse_acc = self.get_gse_chunks(gse)
        index = [(gse_acc, chunk) for chunk in chunks]
        embeddings = fetch_texts_embedding(chunks)
        self.faiss_connector.store_embeddings(index, embeddings)
        self.faiss_connector.save()

    def get_gse_chunks(self, gse: GSE):
        chunks = [gse.title]
        if not self.is_superseries(gse):
            chunks.extend(GSEIndexer.get_chunks(gse.summary))
            chunks.extend(GSEIndexer.get_chunks(gse.overall_design))
        return chunks, gse.gse

    @staticmethod
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

    @staticmethod
    def chunk(gse: GSE):
        chunks = []
