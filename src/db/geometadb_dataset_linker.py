import sqlite3
import json
from typing import List
from src.config.config import Config
from src.db.paper_dataset_linker import PaperDatasetLinker

class GEOmetadbDatasetLinker(PaperDatasetLinker):
    def __init__(self, config: Config):
        self.geometadb_path = config.geometadb_path
    
    def link_to_datasets(self, pubmed_ids: List[str]) -> List[str]:
        if not pubmed_ids:
            raise ValueError("At least one valid PubMed ID is required")
        with sqlite3.connect(self.geometadb_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT gse FROM gse WHERE pubmed_id IN (SELECT value FROM json_each(?))", (json.dumps(pubmed_ids), ))
            results = cursor.fetchall()
            return [result[0] for result in results]