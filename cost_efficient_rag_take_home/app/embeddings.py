"""Embedding provider with an offline, dependency-free fallback for demos/CI."""
import hashlib
import re
import numpy as np
from app.config import settings

class Embedder:
    def __init__(self):
        self.dimension = 384; self.name = settings.embedding_model; self._model = None
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.name)
            self.dimension = self._model.get_sentence_embedding_dimension()
        except ImportError:
            self.name = "local-token-hash-v1 (offline fallback)"

    def encode(self, texts, **_):
        single = isinstance(texts, str); texts = [texts] if single else texts
        if self._model is not None: result = self._model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        else:
            result = np.zeros((len(texts), self.dimension), dtype="float32")
            for i, text in enumerate(texts):
                for token in re.findall(r"[a-z0-9]+", text.lower()):
                    slot = int(hashlib.sha256(token.encode()).hexdigest(), 16) % self.dimension
                    result[i, slot] += 1
                norm = np.linalg.norm(result[i]); result[i] /= norm if norm else 1
        return result[0] if single else result
