"""Fraud Transaction Flagger: rules + per-customer anomaly scoring."""
import argparse
import csv
import statistics
from collections import defaultdict
from datetime import datetime, timedelta

THRESHOLDS = {"step_up": 40, "block": 70}


def load(path):
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    for r in rows:
        r["amount"] = float(r["amount"])
        r["ts"] = datetime.fromisoformat(r["timestamp"])
    return rows


def baselines(history):
    by = defaultdict(list)
    for r in history:
        by[r["customer"]].append(r)
    out = {}
    for c, rows in by.items():
        amts = [r["amount"] for r in rows]
        out[c] = {"mean": statistics.mean(amts), "sd": statistics.pstdev(amts) or 1.0,
                  "devices": {r["device"] for r in rows},
                  "beneficiaries": {r["beneficiary"] for r in rows}}
    return out


def score(tx, base, recent):
    reasons = []
    b = base.get(tx["customer"])
    if b is None:
        reasons.append((30, "no history for customer"))
    else:
        z = (tx["amount"] - b["mean"]) / b["sd"]
        if z > 3:
            reasons.append((40, f"amount is {z:.1f} sd above this customer's normal"))
        elif z > 2:
            reasons.append((20, f"amount is {z:.1f} sd above normal"))
        if tx["device"] not in b["devices"]:
            reasons.append((20, f"new device {tx['device']}"))
        if tx["beneficiary"] not in b["beneficiaries"]:
            reasons.append((15, f"first transfer to {tx['beneficiary']}"))
    if 1 <= tx["ts"].hour < 5:
        reasons.append((15, f"unusual hour {tx['ts']:%H:%M}"))
    window = [r for r in recent[tx["customer"]] if tx["ts"] - r["ts"] <= timedelta(minutes=10)]
    if len(window) >= 3:
        reasons.append((25, f"{len(window) + 1} transactions in 10 minutes"))
    total = sum(p for p, _ in reasons)
    decision = ("BLOCK" if total >= THRESHOLDS["block"] else
                "STEP-UP" if total >= THRESHOLDS["step_up"] else "ALLOW")
    return total, decision, [r for _, r in reasons]


def run(history, incoming):
    base = baselines(history)
    recent = defaultdict(list)
    results = []
    for tx in sorted(incoming, key=lambda r: r["ts"]):
        total, decision, reasons = score(tx, base, recent)
        recent[tx["customer"]].append(tx)
        results.append({**tx, "risk": total, "decision": decision, "reasons": reasons})
    return results


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--history", default="sample_history.csv")
    ap.add_argument("--incoming", default="sample_incoming.csv")
    ap.add_argument("--demo", action="store_true")
    a = ap.parse_args()
    results = run(load(a.history), load(a.incoming))
    for r in results:
        print(f"{r['timestamp']}  {r['customer']:<6} NGN {r['amount']:>10,.0f}  risk {r['risk']:>3}  {r['decision']}")
        for reason in r["reasons"]:
            print(f"      - {reason}")
    counts = {d: sum(r["decision"] == d for r in results) for d in ("ALLOW", "STEP-UP", "BLOCK")}
    print(f"\n{counts}")


if __name__ == "__main__":
    main()
