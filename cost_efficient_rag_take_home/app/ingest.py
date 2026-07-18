import argparse
import logging
from pathlib import Path
from app.chunking import chunks
from app.config import settings
from app.embeddings import Embedder
from app.store import FaissStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

def read_document(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        from pypdf import PdfReader
        return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
    raw = path.read_text(encoding="utf-8", errors="ignore")
    if suffix in {".html", ".htm"}:
        try:
            from bs4 import BeautifulSoup
            return BeautifulSoup(raw, "html.parser").get_text(" ", strip=True)
        except ImportError: return raw
    return raw

def ingest(input_dir: str, reset=False):
    root = Path(input_dir); store = FaissStore(settings.index_dir)
    if reset:
        for file in (store.index_path, store.meta_path):
            if file.exists(): file.unlink()
        store = FaissStore(settings.index_dir)
    rows = []
    for path in sorted(root.rglob("*")):
        if path.suffix.lower() not in {".md", ".html", ".htm", ".pdf"}: continue
        topic = path.stem.split("_")[0]
        rows += chunks(read_document(path), str(path.as_posix()), {"source_type": path.suffix[1:], "topic": topic}, settings.chunk_size, settings.chunk_overlap)
    if not rows: raise ValueError(f"No PDF, HTML, or Markdown documents under {root}")
    model = Embedder(); vectors = model.encode([r["text"] for r in rows])
    inserted = store.upsert(rows, vectors)
    logging.info("candidates=%s inserted=%s total=%s model=%s dimensions=%s", len(rows), inserted, len(store.rows), model.name, vectors.shape[1])
    return inserted

if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--input", required=True); parser.add_argument("--reset", action="store_true")
    args = parser.parse_args(); ingest(args.input, args.reset)
