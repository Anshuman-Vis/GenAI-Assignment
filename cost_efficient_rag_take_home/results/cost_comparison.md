# Cost comparison (USD/month, assumptions stated)

Assumptions: 384-dimension `float32` vectors (1,536 bytes/vector); FAISS Flat index plus 35% metadata/index overhead; an x86 VM at $0.0416/hour ($30.37/month) and gp3-style block storage at $0.08/GB-month. Managed comparison is a conservative illustrative dedicated-vector-pod deployment: $0.111/hour per 1M-vector pod ($81/month), rounded up to capacity, plus $0.10/GB-month storage. Prices are planning assumptions rather than vendor quotes; validate against the provider/region at purchase time. Embedding and LLM tokens are excluded because they are identical across stores.

| Vectors | Estimated FAISS disk | FAISS compute + disk | Managed dedicated capacity | Saving with FAISS |
|---:|---:|---:|---:|---:|
| 100K | 0.19 GB | $30.39 | $81.01 | 62% |
| 1M | 1.93 GB | $30.52 | $81.19 | 62% |
| 10M | 19.31 GB | $31.91 | $812.93 (10 pods) | 96% |

The local estimate keeps one VM on all month, so it is conservative for an on-demand/batch-loaded design. It excludes HA replicas; two replicas roughly double FAISS infrastructure cost. The managed number includes only baseline serving capacity and may be higher once replicas, serverless query usage, egress, or premium features are added.
