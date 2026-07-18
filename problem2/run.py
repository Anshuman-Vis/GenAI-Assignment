import argparse, json, statistics, time, os
from pathlib import Path
from problem2.judge import Judge, asdict

def audit(path, data):
    with path.open("a",encoding="utf-8") as f: f.write(json.dumps(data)+"\n")

def swapped(winner): return {"A":"B","B":"A","TIE":"TIE"}[winner]
def main(suite, output):
    out=Path(output); out.mkdir(parents=True,exist_ok=True); log=out/"judge_audit.jsonl"; log.unlink(missing_ok=True)
    cases=json.loads(Path(suite).read_text())["cases"]; judge=Judge(); rows=[]; calls=0; tokens=0
    for case in cases:
        a,b=case["config_a_output"],case["config_b_output"]
        first=judge.evaluate(case,a,b); second=judge.evaluate(case,b,a); repeat=judge.evaluate(case,a,b)
        va,ua,pa,ra,*xa=first; vb,ub,pb,rb,*xb=second; vr,ur,pr,rr,*xr=repeat; normalized_second=swapped(vb.winner)
        # Require agreement: disagreement becomes tie, avoiding position-biased declaration.
        final=va.winner if va.winner==normalized_second else "TIE"; flip=va.winner!=normalized_second
        padded=a+" " + ("Additional polished but unsupported detail. "*20)
        vp,up,pp,rp,*xp=judge.evaluate(case,padded,b)
        padding_changed=vp.winner != va.winner
        for order,prompt,raw,v,u in [("A_B",pa,ra,va,ua),("B_A",pb,rb,vb,ub),("RETEST_A_B",pr,rr,vr,ur),("PADDED_A_B",pp,rp,vp,up)]:
            audit(log,{"timestamp":time.time(),"case_id":case["id"],"order":order,"judge_prompt":prompt,"raw_response":raw,"parsed_verdict":asdict(v),"usage":u})
            calls+=1; tokens+=sum(u.get(k,0) for k in ("prompt_tokens","completion_tokens","total_tokens"))
        rows.append({"id":case["id"],"first_order_winner":va.winner,"reversed_order_winner":normalized_second,"order_normalized_winner":final,"position_flip":flip,"test_retest_flip":va.winner!=vr.winner,"padding_changed_winner":padding_changed,"mean_criteria":{k:round((va.criteria[k]+vb.criteria[k])/2,2) for k in va.criteria},"gold_winner":case.get("gold_winner")})
    decided=[r for r in rows if r["order_normalized_winner"]!="TIE"]; wins_a=sum(r["order_normalized_winner"]=="A" for r in rows); wins_b=sum(r["order_normalized_winner"]=="B" for r in rows)
    labelled=[r for r in rows if r["gold_winner"]]; agreement=sum(r["order_normalized_winner"]==r["gold_winner"] for r in labelled)/len(labelled) if labelled else None
    mean_scores={criterion:round(statistics.mean(row["mean_criteria"][criterion] for row in rows),2) for criterion in rows[0]["mean_criteria"]}
    report={"mode":"reference-based pairwise; reference-free fallback when expected_output absent","judge_model":judge.model if judge.key else "OFFLINE HEURISTIC (not an LLM)","generator_model":os.getenv("GENERATOR_MODEL","candidate-configs-under-test"),"cases":len(rows),"calls":calls,"tracked_tokens":tokens,"aggregate":{"pass_rate_against_gold":agreement,"mean_criterion_scores":mean_scores},"comparison":{"config_a_wins":wins_a,"config_b_wins":wins_b,"ties":len(rows)-wins_a-wins_b,"winner":"A" if wins_a>wins_b else "B" if wins_b>wins_a else "NO DECLARED WINNER"},"bias":{"position_flip_rate":sum(r["position_flip"] for r in rows)/len(rows),"padding_changed_winner_rate":sum(r["padding_changed_winner"] for r in rows)/len(rows),"mitigation":"both orders required to agree; padded probes measured; ties on disagreement"},"validation":{"gold_agreement_rate":agreement,"test_retest_consistency":1-sum(r["test_retest_flip"] for r in rows)/len(rows),"adversarial_cases":[r for r in rows if "probe" in r["id"]]},"cases_detail":rows}
    (out/"report.json").write_text(json.dumps(report,indent=2)); print(json.dumps(report["comparison"],indent=2))
if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--suite",required=True); p.add_argument("--output",default="problem2/results"); args=p.parse_args(); main(args.suite,args.output)
