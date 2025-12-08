import configparser
import os


class Config:
    """
    Main service configuration. Adapted from PubTrends configuration.
    """

    # Deployment and development
    CONFIG_PATHS = ['/config', os.path.expanduser('~/.pubtrends-datasets')]

    def __init__(self, test=True):
        config_parser = configparser.ConfigParser()

        # Add a fake section [params] for ConfigParser to accept the file
        for config_path in [os.path.join(p, 'config.properties') for p in self.CONFIG_PATHS]:
            if os.path.exists(config_path):
                with open(os.path.expanduser(config_path)) as f:
                    config_parser.read_string("[params]\n" + f.read())
                break
        else:
            raise RuntimeError(f'Configuration file not found among: {self.CONFIG_PATHS}')
        params = config_parser['params']

        self.geometadb_path = params['geometadb_path' if not test else 'test_geometadb_path']
