import unittest
from src.config.config import Config
from src.db.geometadb_gse_loader import GEOmetadbGSELoader
from parameterized import parameterized
from typing import List

from src.test.db.test_datasets import TEST_GSEs

class TestGEOmetadbGSELoader(unittest.TestCase):
    def setUp(self):
        self.test_config = Config(test=True)
        self.GEOmetadb_gse_loader = GEOmetadbGSELoader(self.test_config)

    @parameterized.expand([
        (["GSE116672"], [TEST_GSEs[0]]),
        ([TEST_GSEs[0].gse, TEST_GSEs[1].gse], [TEST_GSEs[0], TEST_GSEs[1]]),
    ])
    def test_load_gses(self, gse_accessions: List[str], expected_gses: List[GSE]):
        gses = self.GEOmetadb_gse_loader.load_gses(gse_accessions)
        gse_ids = list(map(lambda x: x.gse, gses))
        expected_gse_ids = list(map(lambda x: x.gse, expected_gses))
        self.assertListEqual(gse_ids, expected_gse_ids)