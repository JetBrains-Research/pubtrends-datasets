import logging
import os

import numpy as np
import requests

logger = logging.getLogger(__name__)

def fetch_texts_embedding(texts, embeddings_service_url):
    logger.debug('Fetch texts embeddings')
    try:
        r = requests.request(
            url=f'{embeddings_service_url}/embeddings_texts',
            method='GET',
            json=texts,
            headers={'Accept': 'application/json'}
        )
        r.raise_for_status()
        return np.array(r.json()).reshape(len(texts), -1)
    except Exception as e:
        logger.debug(f'Failed to fetch texts embeddings ${e}')
        raise e
