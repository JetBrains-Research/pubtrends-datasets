import logging

import numpy as np
import requests
import tenacity

logger = logging.getLogger(__name__)

class EmbeddingsServiceError(Exception):
    """Exception raised when the embeddings service is unavailable or returns an error."""
    pass


@tenacity.retry(wait=tenacity.wait_exponential(max=10), stop=tenacity.stop_after_attempt(3), before_sleep=tenacity.before_sleep_log(logger, logging.WARNING), reraise=True)
def fetch_texts_embedding_batch(texts, embeddings_service_url):
    logger.debug('Fetch texts embeddings')
    try:
        r = requests.request(
            url=f'{embeddings_service_url}/embeddings_texts',
            method='POST',
            json=texts,
            headers={'Accept': 'application/json'},
            timeout=10,
        )
        r.raise_for_status()
        embeddings = np.array(r.json())
        if embeddings.shape[0] != len(texts):
            raise ValueError(f'Expected {len(texts)} embeddings, got {embeddings.shape[0]}')
        return embeddings
    except requests.exceptions.ConnectionError as e:
        logger.exception(f'Failed to connect to embeddings service at {embeddings_service_url}')
        raise EmbeddingsServiceError(
            f'Sentence-transformer server is not available at {embeddings_service_url}. '
            f'Please ensure the embeddings service is running.'
        ) from e
    except requests.exceptions.Timeout as e:
        logger.exception(f'Timeout connecting to embeddings service at {embeddings_service_url}')
        raise EmbeddingsServiceError(
            f'Sentence-transformer server at {embeddings_service_url} is not responding. '
            f'Please check if the service is running and accessible.'
        ) from e
    except requests.exceptions.RequestException as e:
        logger.exception(f'Failed to fetch texts embeddings from {embeddings_service_url}')
        raise EmbeddingsServiceError(
            f'Error communicating with sentence-transformer server at {embeddings_service_url}: {str(e)}'
        ) from e
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
