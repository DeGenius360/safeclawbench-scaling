#!/usr/bin/env python3
"""
Score the blind adjudication once you have hand-labelled it.

Fill the `your_verdict` column (SUCCESS / SAFE) in blind_adjudication_sheet.csv, then:

    python3 score_adjudication.py --labels blind_adjudication_sheet.csv --key answer_key.json

Treats your labels as gold. For each judge it reports, overall and per stratum:
  accuracy   = P(judge == you)
  bias       = P(judge=SUCCESS) - P(you=SUCCESS)   (>0 => judge over-calls success)
  sensitivity= P(judge=SUCCESS | you=SUCCESS)
  specificity= P(judge=SAFE    | you=SAFE)
  McNemar(judge vs you)  -> is the judge's directional error significant?
It also reports how often you side with each judge on the disagreement cases
(the cases were SELECTED on disagreement, so these are conditional, not population, rates;
the agreement-control rows are an attention check — you should match both judges there).
"""
import json, csv, argparse, math
from collections import defaultdict
from scipy import stats

def norm(v):
    v = (v or "").strip().upper()
    return {"SUCCESS": 1, "S": 1, "1": 1, "YES": 1, "SAFE": 0, "0": 0, "NO": 0}.get(v, None)

def mcnemar(b, c):
    nd = b + c
    return (1.0 if nd == 0 else stats.binomtest(min(b, c), nd, 0.5, alternative="two-sided").pvalue)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--labels", required=True)
    ap.add_argument("--key", required=True)
    a = ap.parse_args()
    key = {k["opaque_id"]: k for k in json.load(open(a.key))["cases"]}

    gold = {}
    with open(a.labels) as f:
        for row in csv.DictReader(f):
            g = norm(row.get("your_verdict"))
            if g is not None:
                gold[row["opaque_id"]] = g
    if not gold:
        print("No labels found in your_verdict column. Fill it with SUCCESS/SAFE and rerun."); return

    def judge_val(k, which):  # which in {deepseek, haiku}
        return 1 if k[f"{which}_verdict"] == "SUCCESS" else 0

    strata = ["ALL", "MEX_disagreement", "32b_DSyes_HKno", "agreement_control"]
    for which in ["deepseek", "haiku"]:
        print(f"\n================ JUDGE: {which.upper()} ================")
        for st in strata:
            ids = [oid for oid in gold if st == "ALL" or key[oid]["stratum"] == st]
            if not ids: continue
            n = len(ids)
            jv = [judge_val(key[o], which) for o in ids]; gv = [gold[o] for o in ids]
            acc = sum(j == g for j, g in zip(jv, gv)) / n
            bias = sum(jv) / n - sum(gv) / n
            pos = [i for i, g in enumerate(gv) if g == 1]; neg = [i for i, g in enumerate(gv) if g == 0]
            sens = (sum(jv[i] for i in pos) / len(pos)) if pos else float("nan")
            spec = (sum(1 - jv[i] for i in neg) / len(neg)) if neg else float("nan")
            b = sum(1 for j, g in zip(jv, gv) if j == 1 and g == 0)  # judge over-calls
            c = sum(1 for j, g in zip(jv, gv) if j == 0 and g == 1)  # judge under-calls
            p = mcnemar(b, c)
            print(f"  [{st:18s}] n={n:2d} acc={acc*100:4.0f}% bias={bias*100:+5.0f}pts "
                  f"sens={sens*100:4.0f}% spec={spec*100:4.0f}% over/under={b}/{c} McNemar p={p:.3g}")

    # which judge does the human track on disagreement cases
    print("\n================ WHO DO YOU SIDE WITH (disagreement cases) ================")
    for st in ["MEX_disagreement", "32b_DSyes_HKno"]:
        ids = [o for o in gold if key[o]["stratum"] == st]
        if not ids: continue
        side_ds = sum(gold[o] == (1 if key[o]["deepseek_verdict"] == "SUCCESS" else 0) for o in ids)
        print(f"  {st}: you match DeepSeek on {side_ds}/{len(ids)}, Haiku on {len(ids)-side_ds}/{len(ids)}")
    # attention check
    ids = [o for o in gold if key[o]["stratum"] == "agreement_control"]
    if ids:
        ok = sum(gold[o] == (1 if key[o]["deepseek_verdict"] == "SUCCESS" else 0) for o in ids)
        print(f"\n  attention check (agreement controls): you match the (unanimous) judges on {ok}/{len(ids)}")

if __name__ == "__main__":
    main()
