# Cost-efficient RAG with FAISS

This submission is a small, reproducible RAG service built around **FAISS** rather than an always-on managed vector database. FAISS is an excellent fit for a large, lightly queried corpus: vectors live on cheap local/block storage, there are no pods to keep warm, and exact search is fast up to millions of vectors. It deliberately trades away multi-region HA, automatic backups, and elastic concurrent serving.

## What is included

* PDF, HTML, and Markdown ingestion with deterministic chunk IDs and idempotent re-ingest.
* Configurable chunking (`CHUNK_SIZE=700`, `CHUNK_OVERLAP=120` by default), embeddings, metadata filters, and persisted FAISS index.
* `POST /ask` HTTP API with top-k retrieval, cited grounded answers, refusal on inadequate evidence, and structured per-query logs.
* A 20-question fixed benchmark with retrieval IR metrics and answer evaluation. Results are checked into `results/evaluation_results.json`.
* Cost model at 100K, 1M, and 10M vectors in `results/cost_comparison.md`.

## Quick start

```bash
python -m venv .venv
.venv/Scripts/activate  # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python -m app.ingest --input data/corpus --reset
uvicorn app.api:app --reload
```

Ask a question:

```bash
curl -X POST http://127.0.0.1:8000/ask -H "Content-Type: application/json" -d "{\"question\":\"What does retrieval augmented generation do?\", \"k\": 4, \"filters\": {\"topic\": \"rag\"}}"
```

Run the benchmark after ingestion:

```bash
python -m evaluation.run_eval
```

The default embedding model is `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions). Set `EMBEDDING_MODEL` to change it. An `OPENAI_API_KEY` is optional: with it, the service calls `gpt-4o-mini` for a strictly contextual answer; without it, it returns a transparent extractive answer so the app remains runnable without a secret.

## API

`POST /ask`

```json
{"question":"How does FAISS persist data?","k":4,"filters":{"source_type":"md"}}
```

Response fields include `answer`, `citations`, `retrieval_latency_ms`, `generation_latency_ms`, `total_latency_ms`, `retrieved_chunk_count`, and `token_usage`. Filter keys are ordinary chunk metadata fields such as `source_type`, `topic`, or `source`.

`GET /health` reports index size and configuration.

## Evaluation design and results

Each of the 20 questions in `evaluation/questions.json` has a gold answer and a relevant source; the harness resolves this to the source's deterministic chunk IDs after ingestion. `evaluation/run_eval.py` calculates Recall@k, Hit Rate, MRR, nDCG@k, and context precision from ranked retrieval. Answer relevance is token-overlap F1 against the gold answer. Faithfulness is a conservative citation-supported claim check: answer sentences must share content terms with their cited evidence. It is deterministic, auditable, and intentionally does **not** present a heuristic as an LLM judge.

See [results/evaluation_results.json](results/evaluation_results.json) for complete per-question output. The checked-in result is a reference run over the included corpus; rerun it on your machine for locally measured latencies.

## Cost discussion

See [results/cost_comparison.md](results/cost_comparison.md). Assumptions are explicit and deliberately separate storage from embedding/API costs. At small scale the operational savings are modest; at 10M vectors, avoiding provisioned always-on capacity dominates. FAISS needs a VM/container and deployment discipline, whereas a managed database supplies HA, backups, observability, filtering, and effortless scaling.

I would switch back to managed vector search when the product requires multi-AZ availability, live writes from many workers, tenant isolation/complex server-side filters, or a team cannot own snapshots and index lifecycle. On the included benchmark the generation layer is the weaker link: retrieval can return the right passage but extractive fallback answers can be less fluent. Supplying `OPENAI_API_KEY` improves synthesis without changing retrieval or storage cost.

## Layout

```
app/          service, ingestion, FAISS store
data/corpus/  small source corpus (MD, HTML, PDF supported by ingestion)
evaluation/   questions and repeatable evaluator
results/      reference evaluation and cost model
```
