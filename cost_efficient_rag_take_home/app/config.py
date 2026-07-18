from dataclasses import dataclass
import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # Environment variables still work in minimal/offline execution.

@dataclass(frozen=True)
class Settings:
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    index_dir: str = os.getenv("INDEX_DIR", "storage")
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "700"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "120"))
    top_k: int = int(os.getenv("TOP_K", "4"))
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

settings = Settings()
