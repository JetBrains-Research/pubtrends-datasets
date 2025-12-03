import unittest
from src.config.config import Config
from src.db.GEOmetadb_dataset_linker import GEOmetadbDatasetLinker
from parameterized import parameterized
from typing import List

class TestGEOmetadbDatasetLinker(unittest.TestCase):
    def setUp(self):
        self.test_config = Config(test=True)
        self.GEOmetadb_dataset_linker = GEOmetadbDatasetLinker(self.test_config)

    @parameterized.expand([
        (["30530648"], ["GSE116672"]),
        (["31018141"], ["GSE127884", "GSE127892", "GSE127893"]),
    ])
    def test_link_to_datasets(self, pubmed_ids: List[str], expected_geo_accessions: List[str]):
        datasets = self.GEOmetadb_dataset_linker.link_to_datasets(pubmed_ids)
        self.assertListEqual(datasets, expected_geo_accessions)