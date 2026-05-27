import configparser
import os


class Config:
    """
    Main service configuration. Adapted from PubTrends configuration.
    """

    # Deployment and development
    CONFIG_PATHS = ['/config', os.path.expanduser('~/.pubtrends-datasets')]

    def __init__(self, test=True, path=None):
        config_parser = configparser.ConfigParser()

        # Add a fake section [params] for ConfigParser to accept the file
        for config_path in [os.path.join(p, 'config.properties') for p in self.CONFIG_PATHS] + ([path] if path else []):
            if os.path.exists(config_path):
                with open(os.path.expanduser(config_path)) as f:
                    config_parser.read_string("[params]\n" + f.read())
                break
        else:
            raise RuntimeError(f'Configuration file not found among: {self.CONFIG_PATHS}')
        params = config_parser['params']

        self.geometadb_path = params['geometadb_path' if not test else 'test_geometadb_path']
        self.geometadb_path = os.path.expanduser(self.geometadb_path)

        self.max_ncbi_connections = self._parse_positive_int(params, 'max_ncbi_connections')

        self.dataset_download_folder = params['dataset_download_folder']
        self.dataset_download_folder = os.path.expanduser(self.dataset_download_folder)

        self.small_dataset_parser_workers = self._parse_positive_int(params, 'small_dataset_parser_workers')
        self.big_dataset_parser_workers = self._parse_positive_int(params, 'big_dataset_parser_workers')
        self.big_gzip_threshold_mb = self._parse_positive_float(params, 'big_gzip_threshold_mb')
        self.archive_parser_chunk_size = self._parse_positive_int(params, 'archive_parser_chunk_size')

        if not os.path.exists(self.dataset_download_folder):
            os.makedirs(self.dataset_download_folder)
        elif not os.path.isdir(self.dataset_download_folder):
            raise RuntimeError(f"{self.dataset_download_folder} is not a directory")
        self.show_backfill_progress = params.getboolean('show_backfill_progress') if not test else False
        self.embeddings_service_url = params['embeddings_service_url']
        if not self.embeddings_service_url.startswith('http'):
            raise ValueError(f"Invalid embeddings_service_url: {self.embeddings_service_url}")
        self.max_tokens_per_chunk = self._parse_nonnegative_int(params, 'max_tokens_per_chunk')
        self.overlap_sentences = self._parse_nonnegative_int(params, 'overlap_sentences')
        self.chunking_workers = self._parse_positive_int(params, 'chunking_workers')
        self.embeddings_batch_size = self._parse_positive_int(params, 'embeddings_batch_size')

    @staticmethod
    def _parse_positive_int(params, key):
        try:
            value = int(params[key])
            if value <= 0:
                raise ValueError(f"{key} must be a positive integer")
            return value
        except ValueError as e:
            raise ValueError(f"Invalid value for {key}: {params[key]}. {e}")

    @staticmethod
    def _parse_nonnegative_int(params, key):
        try:
            value = int(params[key])
            if value < 0:
                raise ValueError(f"{key} must be a non-negative integer")
            return value
        except ValueError as e:
            raise ValueError(f"Invalid value for {key}: {params[key]}. {e}")

    @staticmethod
    def _parse_positive_float(params, key):
        try:
            value = float(params[key])
            if value <= 0:
                raise ValueError(f"{key} must be a positive float")
            return value
        except ValueError as e:
            raise ValueError(f"Invalid value for {key}: {params[key]}. {e}")
