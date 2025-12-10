from typing import List
import sqlite3
import json
from src.config.config import Config
from src.db.gse import GSE
from src.db.gse_loader import GSELoader


class GEOmetadbGSELoader(GSELoader):
    def __init__(self, config: Config) -> None:
        self.geometadb_path = config.geometadb_path
    
    def load_gses(self, gse_accessions: List[str]) -> List[GSE]:
        if not gse_accessions:
            return []
        with sqlite3.connect(self.geometadb_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM gse WHERE gse IN (SELECT value FROM json_each(?))", (json.dumps(gse_accessions), ))
            results = cursor.fetchall()
            return [GSE(*result) for result in results]