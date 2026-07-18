import json
from pathlib import Path
import faiss
import numpy as np

class FaissStore:
    def __init__(self, directory: str):
        self.dir = Path(directory); self.dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.dir / "index.faiss"; self.meta_path = self.dir / "chunks.json"
        self.index = faiss.read_index(str(self.index_path)) if self.index_path.exists() else None
        self.rows = json.loads(self.meta_path.read_text(encoding="utf-8")) if self.meta_path.exists() else []

    def upsert(self, rows, vectors):
        known = {r["id"] for r in self.rows}
        keep = [i for i, r in enumerate(rows) if r["id"] not in known]
        if not keep: return 0
        add = np.asarray(vectors[keep], dtype="float32")
        faiss.normalize_L2(add)
        if self.index is None: self.index = faiss.IndexFlatIP(add.shape[1])
        self.index.add(add); self.rows.extend(rows[i] for i in keep)
        faiss.write_index(self.index, str(self.index_path))
        self.meta_path.write_text(json.dumps(self.rows, indent=2), encoding="utf-8")
        return len(keep)

    def search(self, vector, k, filters=None):
        if self.index is None: return []
        query = np.asarray([vector], dtype="float32"); faiss.normalize_L2(query)
        scores, ids = self.index.search(query, min(self.index.ntotal, max(k * 8, k)))
        found = []
        for score, idx in zip(scores[0], ids[0]):
            if idx < 0: continue
            row = dict(self.rows[idx])
            if filters and any(str(row.get(key)) != str(value) for key, value in filters.items()): continue
            row["score"] = round(float(score), 5); found.append(row)
            if len(found) == k: break
        return found
