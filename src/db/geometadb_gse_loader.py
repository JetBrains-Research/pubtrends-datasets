from typing import List
import sqlite3
import json
from db.gse import GSE
from src.db.gse_loader import GSELoader


class GEOmetadbGSELoader(GSELoader):
    def __init__(self, GEOmetadb_path) -> None:
        self.GEOmetadb_path = GEOmetadb_path
        self.conn = sqlite3.connect(self.GEOmetadb_path)
    
    def load_gses(self, gse_accessions: List[str]) -> List[GSE]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM gse WHERE gse IN (SELECT value FROM json_each(?))", (json.dumps(gse_accessions), ))
        results = cursor.fetchall()
        return [GSE(**result) for result in results]