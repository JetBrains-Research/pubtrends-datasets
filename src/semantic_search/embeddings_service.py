import logging
import os

import numpy as np
import requests

logger = logging.getLogger(__name__)
EMBEDDINGS_SERVICE_URL = os.getenv('EMBEDDINGS_SERVICE_URL', '').rstrip('/')

def fetch_texts_embedding(texts):
    # Don't use the model as is, since each celery process will load its own copy.
    # Shared model is available via additional service with a single model.
    if not EMBEDDINGS_SERVICE_URL:
        logger.debug('Embeddings service URL is not configured')
        return None
    logger.debug('Fetch texts embeddings')
    try:
        r = requests.request(
            url=f'{EMBEDDINGS_SERVICE_URL}/embeddings_texts',
            method='GET',
            json=texts,
            headers={'Accept': 'application/json'}
        )
        if r.status_code == 200:
            return np.array(r.json()).reshape(len(texts), -1)
        logger.debug(f'Wrong response code {r.status_code}')
    except Exception as e:
        logger.debug(f'Failed to fetch texts embeddings ${e}')
    return None
