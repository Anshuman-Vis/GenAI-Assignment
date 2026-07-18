import logging, os, time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from app.config import settings
from app.embeddings import Embedder
from app.store import FaissStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
app = FastAPI(title="Cost-efficient FAISS RAG")
model = None

class Ask(BaseModel):
    question: str = Field(min_length=3)
    k: int = Field(default=settings.top_k, ge=1, le=20)
    filters: dict[str, str] | None = None

def embedder():
    global model
    if model is None: model = Embedder()
    return model

def answer(question, evidence):
    if not evidence or evidence[0]["score"] < 0.25:
        return "I don't have relevant context in the indexed documents to answer that.", {"input_tokens": 0, "output_tokens": 0}
    context = "\n\n".join(f"[{x['id']}] {x['text']}" for x in evidence)
    if os.getenv("OPENAI_API_KEY"):
        from openai import OpenAI
        response = OpenAI().chat.completions.create(model=settings.openai_model, temperature=0,
          messages=[{"role":"system","content":"Answer only from supplied context. Cite chunk IDs in brackets. If unsupported, say no relevant context."}, {"role":"user","content":f"Context:\n{context}\n\nQuestion: {question}"}])
        usage = response.usage
        return response.choices[0].message.content, {"input_tokens": usage.prompt_tokens, "output_tokens": usage.completion_tokens}
    # Explicit, grounded fallback for no-key demos.
    return evidence[0]["text"] + f" [{evidence[0]['id']}]", {"input_tokens": 0, "output_tokens": 0}

@app.get("/health")
def health():
    store = FaissStore(settings.index_dir)
    return {"ok": True, "vectors": len(store.rows), "embedding_model": settings.embedding_model, "dimensions": store.index.d if store.index else None}

@app.post("/ask")
def ask(payload: Ask):
    begun = time.perf_counter(); store = FaissStore(settings.index_dir)
    if not store.rows: raise HTTPException(503, "Index is empty. Run ingestion first.")
    retrieval_start = time.perf_counter()
    vector = embedder().encode(payload.question)
    evidence = store.search(vector, payload.k, payload.filters)
    retrieval_ms = (time.perf_counter() - retrieval_start) * 1000
    generation_start = time.perf_counter(); text, usage = answer(payload.question, evidence)
    generation_ms = (time.perf_counter() - generation_start) * 1000; total_ms = (time.perf_counter() - begun) * 1000
    result = {"answer": text, "citations": [{"chunk_id": x["id"], "source": x["source"], "score": x["score"]} for x in evidence], "retrieved_chunk_count": len(evidence), "retrieval_latency_ms": round(retrieval_ms, 2), "generation_latency_ms": round(generation_ms, 2), "total_latency_ms": round(total_ms, 2), "token_usage": usage}
    logging.info("query=%r chunks=%s retrieval_ms=%.2f generation_ms=%.2f total_ms=%.2f tokens=%s", payload.question, len(evidence), retrieval_ms, generation_ms, total_ms, usage)
    return result
