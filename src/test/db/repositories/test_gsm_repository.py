import unittest
import os
from typing import List

from src.config.config import Config
from src.db.repositories.gsm_repository import GSMRepository
from src.db.models.gsm import GSM


class TestGSMRepository(unittest.TestCase):
    def setUp(self):
        self.test_config = Config(test=True)
        self.repository = GSMRepository(self.test_config.geometadb_path)

    def test_get_gsms_empty_list(self):
        """Test that empty list returns empty result."""
        gsms = self.repository.get_gsms([])
        self.assertEqual(len(gsms), 0)

    def test_get_gsms_nonexistent(self):
        """Test that nonexistent GSMs return empty list."""
        gsms = self.repository.get_gsms(["GSM_NONEXISTENT_123"])
        self.assertEqual(len(gsms), 0)

    def test_save_and_retrieve_gsms(self):
        """Test saving and retrieving GSMs."""
        test_gsm = GSM(
            gsm="GSM_TEST_001",
            title="Test Sample",
            series_id="GSE12345",
            status="Public",
            type="RNA"
        )

        self.repository.save_gsms([test_gsm])
        retrieved = self.repository.get_gsms(["GSM_TEST_001"])

        self.assertEqual(len(retrieved), 1)
        self.assertEqual(retrieved[0].gsm, "GSM_TEST_001")
        self.assertEqual(retrieved[0].title, "Test Sample")

    def test_save_empty_list(self):
        """Test that saving empty list doesn't cause errors."""
        self.repository.save_gsms([])
        # Should complete without error

    def test_repository_initialization_invalid_path(self):
        """Test that repository raises error with invalid path."""
        with self.assertRaises(RuntimeError):
            GSMRepository("/nonexistent/path/to/db.sqlite")
