# FAISS operations

FAISS is a vector similarity-search library. IndexFlatIP performs exact inner-product search; normalized vectors make inner product equivalent to cosine similarity. It has no mandatory server process and an index can be persisted to a file with write_index and loaded with read_index.

FAISS is economical for lightly queried workloads because it can run on a small VM and read an index from local or attached block storage. The application owns snapshots, replicas, access control, and rolling index updates. For high availability, multi-region traffic, complex server-side filtering, or high-concurrency writes, a managed vector service may be preferable.

At larger scale, IVF or HNSW indexes reduce query work but introduce recall/latency tuning. Exact Flat search is a useful correctness baseline on a small corpus.
