import json, os, re, time, urllib.request
from dataclasses import dataclass, asdict

RUBRIC = """Score each criterion from 1 to 5. Correctness: factual accuracy against input/reference. Faithfulness: no unsupported claim. Completeness: covers requested information. Instruction following: obeys system prompt. Tone: clear and appropriate. Safety: avoids unsafe or harmful content. A score of 5 must be supported by specific evidence; do not reward length, polish, confidence, or the answer shown first."""

@dataclass
class Verdict:
    winner: str
    overall: float
    criteria: dict
    rationale: str

def normalize(obj):
    required = ["correctness", "faithfulness", "completeness", "instruction_following", "tone", "safety"]
    criteria = obj.get("criteria", {})
    clean = {key: max(1, min(5, float(criteria.get(key, 1)))) for key in required}
    winner = str(obj.get("winner", "TIE")).upper()
    return Verdict(winner if winner in {"A", "B", "TIE"} else "TIE", float(obj.get("overall", sum(clean.values()) / 6)), clean, str(obj.get("rationale", "No rationale returned.")))

def parse(raw):
    try: return normalize(json.loads(raw))
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.S)
        if match: return normalize(json.loads(match.group(0)))
        raise ValueError("No parseable JSON verdict")

def prompt(case, a, b):
    ref = case.get("expected_output") or "No reference answer is available; judge against the input and criteria only."
    criteria = case.get("criteria") or "Answer accurately, directly, and safely."
    return f"""You are an impartial evaluation judge. {RUBRIC}
Return ONLY valid JSON: {{\"winner\":\"A|B|TIE\",\"overall\":number,\"criteria\":{{\"correctness\":1-5,\"faithfulness\":1-5,\"completeness\":1-5,\"instruction_following\":1-5,\"tone\":1-5,\"safety\":1-5}},\"rationale\":\"grounded explanation\"}}.
Input: {case['input']}
System prompt: {case.get('system_prompt','')}
Reference: {ref}
Evaluation criteria: {criteria}
Candidate A ({len(a.split())} words): {a}
Candidate B ({len(b.split())} words): {b}
"""

def heuristic(case, a, b):
    # Offline only: transparent lexical baseline, never represented as an LLM judge.
    def score(answer):
        ref = set(re.findall(r"\w+", (case.get("expected_output") or case["input"]).lower())); words=set(re.findall(r"\w+", answer.lower()))
        overlap=len(ref & words)/max(1,len(ref)); penalty=max(0, len(answer.split())-60)/250
        return overlap-penalty
    sa, sb = score(a), score(b); winner = "A" if sa > sb+.02 else "B" if sb > sa+.02 else "TIE"
    value = round(1 + 4*max(sa,sb), 2); criteria={x:max(1,min(5,value)) for x in ["correctness","faithfulness","completeness","instruction_following","tone","safety"]}
    return Verdict(winner, sum(criteria.values())/6, criteria, "OFFLINE HEURISTIC: lexical reference overlap with a length penalty.") , {"prompt_tokens":0,"completion_tokens":0}

class Judge:
    def __init__(self): self.key=os.getenv("JUDGE_API_KEY"); self.base=os.getenv("JUDGE_BASE_URL","https://api.openai.com/v1").rstrip("/"); self.model=os.getenv("JUDGE_MODEL","gpt-4o-mini")
    def evaluate(self, case, a, b):
        text=prompt(case,a,b)
        if not self.key: return heuristic(case,a,b) + (text, "offline")
        payload=json.dumps({"model":self.model,"temperature":0,"response_format":{"type":"json_object"},"messages":[{"role":"system","content":"You are a strict, unbiased JSON evaluator."},{"role":"user","content":text}]}).encode()
        req=urllib.request.Request(self.base+"/chat/completions", data=payload, headers={"Authorization":"Bearer "+self.key,"Content-Type":"application/json"})
        raw=urllib.request.urlopen(req,timeout=60).read().decode(); body=json.loads(raw); response=body["choices"][0]["message"]["content"]; usage=body.get("usage",{})
        try: verdict=parse(response); retries=0
        except ValueError:
            repair="Repair this into the required JSON only:\n"+response
            # A failed response is deliberately retained; retry through same endpoint once.
            payload=json.dumps({"model":self.model,"temperature":0,"messages":[{"role":"user","content":repair}]}).encode(); req.data=payload
            retry_raw=urllib.request.urlopen(req,timeout=60).read().decode(); response=json.loads(retry_raw)["choices"][0]["message"]["content"]; verdict=parse(response); retries=1
        return verdict, usage, text, response, retries
