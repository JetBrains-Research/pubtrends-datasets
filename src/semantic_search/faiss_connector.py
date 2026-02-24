import logging
import os
import re

import faiss
import numpy as np
import pandas as pd

HNSW_M = 32
HNSW_EF_CONSTRUCTION = 128
HNSW_EF_SEARCH = 32


logger = logging.getLogger(__name__)

FAISS_PATHS = ['/faiss', os.path.expanduser('~/.pubtrends-datasets/faiss')]
for p in FAISS_PATHS:
    if os.path.isdir(p):
        faiss_path = p
        break
else:
    raise RuntimeError('Failed to configure faiss directory')


class FaissConnector:
    def __init__(self, source, embeddings_model_name, embeddings_dimension, create=True, exact=False):
        self.embeddings_dimension = embeddings_dimension
        self.create = create
        self.exact = exact
        folder_name = re.sub('[^a-zA-Z0-9]', '_', embeddings_model_name)
        self.faiss_dir = f'{faiss_path}/faiss_{source}_{folder_name}'
        if not os.path.exists(self.faiss_dir):
            if not self.create:
                raise Exception(f'Faiss directory {self.faiss_dir} does not exist')
            os.makedirs(self.faiss_dir)
        self.faiss_index_file = os.path.expanduser(f'{self.faiss_dir}/embeddings.index')
        self.gse_acc_index_file = os.path.expanduser(f'{self.faiss_dir}/gse_accs.pq')
        self.create_or_load_faiss()

    def create_faiss(self):
        if self.exact:
            print('Exact search index')
            index = faiss.IndexFlatIP(self.embeddings_dimension)
        else:
            print('Approximate search index')
            index = faiss.IndexHNSWFlat(self.embeddings_dimension, HNSW_M)
            index.hnsw.efConstruction = HNSW_EF_CONSTRUCTION
            index.hnsw.efSearch = HNSW_EF_SEARCH
        return index

    def create_or_load_faiss(self):
        if os.path.exists(self.faiss_index_file):
            print(f'Loading Faiss index from existing file {self.faiss_index_file}')
            faiss_index = faiss.read_index(self.faiss_index_file)
            faiss_index.hnsw.efSearch = HNSW_EF_SEARCH
            faiss_index.hnsw.efConstruction = HNSW_EF_CONSTRUCTION
        else:
            if not self.create:
                raise Exception(f'Faiss index file {self.faiss_index_file} does not exist')
            print(f'Creating empty Faiss index {self.faiss_index_file}')
            faiss_index = self.create_faiss()
        if os.path.exists(self.gse_acc_index_file):
            print(f'Loading Ids index from existing file {self.gse_acc_index_file}')
            gse_acc_idx = pd.read_parquet(self.gse_acc_index_file)
        else:
            if not self.create:
                raise Exception(f'Ids index file {self.gse_acc_index_file} does not exist')
            gse_acc_idx = pd.DataFrame(data=[], columns=['gse_acc', 'chunk'], dtype=int)
            print(f'Creating empty Ids index {self.gse_acc_index_file}')
        self.gse_acc_idx = gse_acc_idx
        self.faiss_index = faiss_index
        return faiss_index, gse_acc_idx

    def store_embeddings(self, index, embeddings):
        embeddings = np.array(embeddings).astype('float32')
        if (len(embeddings.shape) == 1 or
                embeddings.shape[1] != self.embeddings_dimension or
                len(index) != embeddings.shape[0]):
            print(f'Problematic chunk embeddings, {embeddings.shape}')
            return
        t = pd.DataFrame(data=index, columns=['gse_acc', 'chunk'])
        self.gse_acc_idx = pd.concat([self.gse_acc_idx, t], ignore_index=True).reset_index(drop=True)
        self.faiss_index.add(embeddings)

    def save(self):
        assert len(self.gse_acc_idx) == self.faiss_index.ntotal
        print(f'Storing FAISS index {self.faiss_index_file}')
        faiss.write_index(self.faiss_index, self.faiss_index_file)
        print(f'Storing Ids index {self.gse_acc_index_file} with {len(self.gse_acc_idx)} rows')
        self.gse_acc_idx.to_parquet(self.gse_acc_index_file, index=False, compression='gzip')

    def is_gse_in_index(self, gse_acc):
        return gse_acc in self.gse_acc_idx['gse_acc'].values