# Problem 2 — LLM-as-Judge Evaluation Pipeline

`python -m problem2.run --suite problem2/data/suite.json --output problem2/results` evaluates two candidate configurations for every test case. It uses **reference-based pairwise judging** when a gold answer is supplied, and reference-free pairwise judging otherwise. Pairwise is selected because it is better suited to choosing between a prompt/model A and B than independent pointwise scores alone.

## Run

```powershell
Copy-Item problem2/.env.example problem2/.env
# Set JUDGE_API_KEY in problem2/.env for a real LLM judge.
python -m problem2.run --suite problem2/data/suite.json --output problem2/results
```

The standard library-only offline judge is used if `JUDGE_API_KEY` is unset. It makes the pipeline demonstrable without secrets but is **not** an LLM and must not be used as a release gate. With a key, `JUDGE_BASE_URL`, `JUDGE_MODEL`, and `GENERATOR_MODEL` are independently configured.

## Rubric and verdict

The judge must emit JSON with scores from 1–5 and a grounded rationale for `correctness`, `faithfulness`, `completeness`, `instruction_following`, `tone`, and `safety`, plus `winner` (`A`, `B`, or `TIE`) and `overall`. The prompt explicitly directs it not to reward length, style, confidence, or answer position; it requires evidence tied to the input/reference.

## Bias controls

* **Position bias:** every pair is judged A/B and B/A; the report uses the order-normalized winner and reports flip rate.
* **Verbosity bias:** answers are length-controlled in the rubric; each suite also gets a padded-answer probe and reports whether padding changed the winner.
* **Self-enhancement:** `JUDGE_MODEL` and `GENERATOR_MODEL` are separate variables; use a judge from a different model family in production.
* **Sycophancy/style:** the prompt requires grounded criterion rationales and the suite includes confidently wrong and terse-correct probes.
* **Score clustering:** 1–5 anchored rubric language is included in every prompt; pairwise winner is the release-comparison decision rather than a single coarse score.

## Auditability and safety

Every call writes JSONL containing timestamp, complete prompt, raw response, parsed verdict, retry count, and token/call usage. Malformed JSON is handled by extracting a JSON object, then retrying once with a repair prompt; failed parses are recorded rather than silently accepted.

The checked-in report is an offline fallback run. It validates pipeline mechanics and exposes probe outcomes, but it does not establish LLM-judge quality. Before gating a release, run the same suite with an independent judge and obtain blinded human labels for a larger, representative sample.
