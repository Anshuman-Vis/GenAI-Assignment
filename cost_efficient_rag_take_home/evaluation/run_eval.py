"""Repeatable offline evaluation. Run ingestion first, then: python -m evaluation.run_eval"""
import json, math, re, statistics, time
from pathlib import Path
from app.config import settings
from app.embeddings import Embedder
from app.store import FaissStore

ROOT = Path(__file__).parents[1]
def terms(text): return {x for x in re.findall(r"[a-z0-9]+", text.lower()) if len(x) > 2}
def f1(a, b):
    aa, bb = terms(a), terms(b); shared = len(aa & bb)
    return 0 if not shared else 2 * shared / (len(aa) + len(bb))

def main(k=4):
    queries = json.loads((ROOT / "evaluation/questions.json").read_text())
    store = FaissStore(settings.index_dir)
    if not store.rows: raise RuntimeError("Empty index; run python -m app.ingest --input data/corpus --reset")
    model = Embedder()
    latencies=[]; records=[]; recalls=[]; hits=[]; mrrs=[]; ndcgs=[]; precisions=[]; faithful=[]; relevance=[]
    for q in queries:
        gold = {r["id"] for r in store.rows if r["source"] == q["relevant_source"]}
        started=time.perf_counter(); got=store.search(model.encode(q["question"]), k); latencies.append((time.perf_counter()-started)*1000)
        ranks=[i+1 for i,r in enumerate(got) if r["id"] in gold]
        hit=bool(ranks); recall=float(hit) # one source passage is the task-relevant unit
        rr=1/ranks[0] if ranks else 0
        dcg=sum(1/math.log2(i+2) for i,r in enumerate(got) if r["id"] in gold); ideal=sum(1/math.log2(i+2) for i in range(min(k,len(gold))))
        ndcg=dcg/ideal if ideal else 0; precision=sum(r["id"] in gold for r in got)/len(got) if got else 0
        # Evaluation is offline and deterministic; mirrors the service's no-key extractive mode.
        generated = got[0]["text"] if got and got[0]["score"] >= .25 else "I don't have relevant context."
        rel=f1(generated, q["gold_answer"])
        # Citation/evidence lexical support; each nontrivial answer sentence must overlap retrieved text.
        evidence=" ".join(r["text"] for r in got); claims=[s for s in re.split(r"[.!?]", generated) if len(terms(s)) >= 3]
        faith=sum(bool(terms(s)&terms(evidence)) for s in claims)/len(claims) if claims else 1
        recalls.append(recall); hits.append(hit); mrrs.append(rr); ndcgs.append(ndcg); precisions.append(precision); faithful.append(faith); relevance.append(rel)
        records.append({"id":q["id"],"retrieved_ids":[r["id"] for r in got],"relevant_ids":sorted(gold),"recall_at_k":recall,"reciprocal_rank":rr,"ndcg_at_k":ndcg,"context_precision":precision,"faithfulness":faith,"answer_relevance_f1":rel})
    latencies.sort(); p=lambda v: round(v,4)
    output={"run_configuration":{"store":"FAISS IndexFlatIP","embedding_model":model.name,"dimensions":store.index.d,"k":k,"questions":len(queries),"answer_mode":"OpenAI grounded generation if OPENAI_API_KEY is set; otherwise extractive cited fallback"},"retrieval":{"recall_at_k":p(statistics.mean(recalls)),"hit_rate":p(statistics.mean(hits)),"mrr":p(statistics.mean(mrrs)),"ndcg_at_k":p(statistics.mean(ndcgs)),"context_precision":p(statistics.mean(precisions)),"latency_ms":{"p50":p(statistics.median(latencies)),"p95":p(latencies[math.ceil(.95*len(latencies))-1])}},"answer":{"faithfulness":p(statistics.mean(faithful)),"answer_relevance_f1":p(statistics.mean(relevance)),"method":"deterministic lexical support / gold-answer token F1; replace with blinded LLM judge for production-quality semantic assessment"},"per_question":records}
    out=ROOT/"results/evaluation_results.json"; out.parent.mkdir(exist_ok=True); out.write_text(json.dumps(output,indent=2)); print(json.dumps(output["retrieval"],indent=2))
if __name__ == "__main__": main()
