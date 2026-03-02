import logging
import os

import numpy as np
import requests
import tenacity

logger = logging.getLogger(__name__)

@tenacity.retry(wait=tenacity.wait_exponential(max=10), stop=tenacity.stop_after_attempt(3))
def fetch_texts_embedding_batch(texts, embeddings_service_url):
    logger.debug('Fetch texts embeddings')
    try:
        r = requests.request(
            url=f'{embeddings_service_url}/embeddings_texts',
            method='GET',
            json=texts,
            headers={'Accept': 'application/json'}
        )
        r.raise_for_status()
        embeddings = np.array(r.json())
        if embeddings.shape[0] != len(texts):
            raise ValueError(f'Expected {len(texts)} embeddings, got {embeddings.shape[0]}')
        return embeddings
    except Exception as e:
        logger.exception(f'Failed to fetch texts embeddings')
        raise e

def fetch_texts_embedding(texts, embeddings_service_url, batch_size=64):
    texts_batches = []
    for i in range(0, len(texts), batch_size):
        texts_batches.append(texts[i:i + batch_size])
    embeddings = []
    for texts_batch in texts_batches:
        embeddings.extend(fetch_texts_embedding_batch(texts_batch, embeddings_service_url))
    embeddings = np.vstack(embeddings)
    if len(embeddings) != len(texts):
        raise ValueError(f'Expected {len(texts)} embeddings, got {embeddings.shape[0]}')
    return embeddings
