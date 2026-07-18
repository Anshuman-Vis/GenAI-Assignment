# Retrieval augmented generation

Retrieval augmented generation (RAG) retrieves passages from a trusted corpus before generating an answer. The language model receives the question and the retrieved passages, which reduces unsupported answers and lets the application cite its sources. Retrieval quality matters: an answer cannot be grounded if the relevant passage is absent from the top results.

Chunking divides a document into smaller passages. Overlap preserves a little context at chunk boundaries, but excessive overlap creates near-duplicate vectors and raises storage cost. A common starting point is 700 characters with 120 characters of overlap, then tune against a labelled retrieval set.

Metadata filters narrow retrieval to a trusted source, topic, or tenant. Filtering after an approximate search can miss candidates, so high-selectivity production filters should be incorporated into the index or searched with a larger candidate pool.
