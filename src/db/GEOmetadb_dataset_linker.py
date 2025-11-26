import sqlite3
import json
from typing import List
from src.db.paper_dataset_linker import PaperDatasetLinker

class GEOmetadbDatasetLinker(PaperDatasetLinker):
    def __init__(self, GEOmetadb_path: str):
        self.GEOmetadb_path = GEOmetadb_path
        self.conn = sqlite3.connect(self.GEOmetadb_path)
    
    def link_to_datasets(self, pubmed_ids: List[str]) -> List[str]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT gse FROM gse WHERE pubmed_id IN (SELECT value FROM json_each(?))", (json.dumps(pubmed_ids), ))
        results = cursor.fetchall()
        return [result[0] for result in results]