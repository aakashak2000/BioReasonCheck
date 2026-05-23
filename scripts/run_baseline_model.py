"""
BioReasonCheck-FI · run_baseline_model.py
Run the test-split benchmark prompts against a baseline model (any
OpenAI-compatible chat completions endpoint) and compare with L-LLM results.

Requires environment variables:
  BASELINE_ENDPOINT_URL — full URL to /v1/chat/completions
  BASELINE_API_TOKEN    — bearer token
  BASELINE_MODEL_NAME   — model identifier sent in the payload (default: baseline)

Usage:
  python scripts/run_baseline_model.py
  python scripts/run_baseline_model.py --dry-run
  python scripts/run_baseline_model.py --format-filter ternary
"""
import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")

MAX_TOKENS = 200
TEMPERATURE = 0.0


# ─────────────────────────── parsing (same as run_llm.py) ────────────────────

def parse_binary(text: str) -> str:
    matches = re.findall(r"\b(yes|no)\b", text, re.IGNORECASE)
    if not matches:
        return "UNPARSEABLE"
    unique = {m.upper() for m in matches}
    return unique.pop() if len(unique) == 1 else "UNPARSEABLE"


def parse_ternary(text: str) -> str:
    for label in ["NOT_SUPPORTED", "INSUFFICIENT_EVIDENCE", "SUPPORTED"]:
        if re.search(rf"\b{re.escape(label)}\b", text, re.IGNORECASE):
            return label.upper()
    return "UNPARSEABLE"


def parse_mcq(text: str, correct_option: str, gold_label: str) -> str:
    lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
    search_text = "\n".join(lines[-5:]) if lines else text
    matches = re.findall(r"(?<![A-Za-z])([A-D])(?![A-Za-z])", search_text, re.IGNORECASE)
    if not matches:
        matches = re.findall(r"(?<![A-Za-z])([A-D])(?![A-Za-z])", text, re.IGNORECASE)
    if not matches:
        return "UNPARSEABLE"
    unique = {m.upper() for m in matches}
    if len(unique) > 1:
        return "UNPARSEABLE"
    chosen = unique.pop()
    return gold_label if chosen == correct_option else (
        "NOT_" + gold_label if gold_label == "SUPPORTED" else "SUPPORTED"
    )


def parse_response(entry: dict, raw_output: str) -> str:
    fmt = entry["format_type"]
    if fmt == "binary":
        return parse_binary(raw_output)
    if fmt == "ternary":
        return parse_ternary(raw_output)
    if fmt == "mcq":
        return parse_mcq(raw_output, entry.get("correct_option", ""), entry["gold_label"])
    return "UNPARSEABLE"


def is_correct(parsed: str, entry: dict) -> bool:
    fmt = entry["format_type"]
    if parsed == "UNPARSEABLE":
        return False
    if fmt == "binary":
        return parsed == entry["correct_answer"]
    return parsed == entry["gold_label"]


# ─────────────────────────── API call ────────────────────────────────────────

def call_baseline(messages: list[dict], endpoint: str, token: str,
                  model_name: str, retries: int = 2) -> dict:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model_name,
        "messages": messages,
        "max_tokens": MAX_TOKENS,
        "temperature": TEMPERATURE,
    }
    for attempt in range(retries + 1):
        try:
            resp = requests.post(endpoint, headers=headers, json=payload, timeout=60)
            if resp.status_code == 429:
                if attempt < retries:
                    time.sleep(5)
                    continue
                return {"error": "ERROR:429"}
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"].get("content", "")
            return {"content": content or ""}
        except Exception as e:
            print(f"  [WARN] Attempt {attempt+1} failed: {e}")
            if attempt < retries:
                time.sleep(2)
    return {"error": "ERROR"}


# ─────────────────────────── comparison ──────────────────────────────────────

def compare_results(lllm_path: Path, baseline_path: Path) -> dict:
    """Compute per-format accuracy and FIR for both models."""
    def load_jsonl(p):
        rows = []
        with open(p) as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        return rows

    lllm = {r["id"]: r for r in load_jsonl(lllm_path)}
    baseline = {r["id"]: r for r in load_jsonl(baseline_path)}

    results = {"lllm": {}, "baseline": {}}
    for model_name, data in [("lllm", lllm), ("baseline", baseline)]:
        for fmt in ["binary", "ternary", "mcq"]:
            sub = [r for r in data.values()
                   if r["format_type"] == fmt and r["parsed_label"] != "UNPARSEABLE"]
            if not sub:
                continue
            n_correct = sum(1 for r in sub if is_correct(r["parsed_label"], r))
            results[model_name][fmt] = {
                "accuracy": round(n_correct / len(sub), 4),
                "n": len(sub),
            }

    # FIR
    for model_name, data in [("lllm", lllm), ("baseline", baseline)]:
        from collections import defaultdict
        by_fact = defaultdict(dict)
        for r in data.values():
            if r["parsed_label"] != "UNPARSEABLE":
                by_fact[r["fact_id"]][r["format_type"]] = is_correct(r["parsed_label"], r)
        unstable = sum(
            1 for fid, fmts in by_fact.items()
            if len(fmts) >= 2 and len(set(fmts.values())) > 1
        )
        total = sum(1 for fid, fmts in by_fact.items() if len(fmts) >= 2)
        results[model_name]["fir"] = round(unstable / total, 4) if total > 0 else 0.0
        results[model_name]["fir_unstable"] = unstable
        results[model_name]["fir_total"] = total

    return results


# ─────────────────────────── main ────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Run baseline model on test split")
    parser.add_argument("--input", type=Path,
                        default=ROOT / "data" / "processed" / "benchmark.jsonl")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "outputs" / "baseline_outputs.jsonl")
    parser.add_argument("--lllm-outputs", type=Path,
                        default=ROOT / "outputs" / "model_outputs.jsonl")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--format-filter", default=None,
                        choices=["binary", "ternary", "mcq"])
    args = parser.parse_args()

    # ── Env checks ──
    endpoint = os.getenv("BASELINE_ENDPOINT_URL", "").strip()
    token = os.getenv("BASELINE_API_TOKEN", "").strip()
    model_name = os.getenv("BASELINE_MODEL_NAME", "baseline").strip()

    if not endpoint or not token:
        print("[ERROR] Missing environment variables.")
        print("  Set BASELINE_ENDPOINT_URL and BASELINE_API_TOKEN to run comparison.")
        print("  Example:")
        print("    export BASELINE_ENDPOINT_URL=https://api.openai.com/v1/chat/completions")
        print("    export BASELINE_API_TOKEN=sk-...")
        print("    export BASELINE_MODEL_NAME=gpt-4o-mini  # optional, default: baseline")
        sys.exit(1)

    # ── Load benchmark ──
    entries = []
    with open(args.input, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))

    # Filter to test split only
    entries = [e for e in entries if e.get("split") == "test"]
    if args.format_filter:
        entries = [e for e in entries if e["format_type"] == args.format_filter]

    print(f"[INFO] Baseline: {model_name} @ {endpoint}")
    print(f"[INFO] {len(entries)} test prompts to evaluate")

    if args.dry_run:
        print(f"\n[DRY-RUN] First 2 prompts:")
        for e in entries[:2]:
            print(f"  {e['id']} ({e['format_type']}) | gold={e['gold_label']}")
            print(f"  {e['messages'][-1]['content'][:100]}")
        return

    # ── Run ──
    args.output.parent.mkdir(parents=True, exist_ok=True)
    results = []
    correct_count = 0
    parse_ok = 0

    with open(args.output, "w", encoding="utf-8") as out_f:
        for i, entry in enumerate(entries):
            print(f"┌─ {i+1}/{len(entries)} {entry['id']} ({entry['format_type']}) gene={entry['gene']}")
            print(f"│  gold={entry['gold_label']}", end="  ")

            result = call_baseline(entry["messages"], endpoint, token, model_name)
            is_error = "error" in result
            content = result.get("content", "")
            raw_output = result.get("error", content)
            parsed = parse_response(entry, content) if not is_error else "UNPARSEABLE"
            correct = is_correct(parsed, entry)

            if parsed != "UNPARSEABLE":
                parse_ok += 1
            if correct:
                correct_count += 1

            status = "✓" if correct else "✗"
            acc_so_far = correct_count / (i + 1) * 100
            print(f"parsed={parsed}  {status}  (acc={acc_so_far:.0f}%)")

            rec = {
                "id": entry["id"],
                "fact_id": entry["fact_id"],
                "gene": entry["gene"],
                "format_type": entry["format_type"],
                "split": entry["split"],
                "gold_label": entry["gold_label"],
                "correct_answer": entry["correct_answer"],
                "correct_option": entry.get("correct_option", ""),
                "raw_output": raw_output,
                "parsed_label": parsed,
            }
            out_f.write(json.dumps(rec) + "\n")
            out_f.flush()
            results.append(rec)

            if not is_error:
                time.sleep(0.5)

    total = len(results)
    print(f"\n[Done] {total} outputs → {args.output}")
    print(f"       Parse success: {parse_ok}/{total} ({parse_ok/total*100:.1f}%)")

    # ── Compare with L-LLM ──
    if args.lllm_outputs.exists():
        print(f"\n── Comparison: L-LLM vs {model_name} ──")
        comp = compare_results(args.lllm_outputs, args.output)
        print(f"  {'metric':<20} {'L-LLM':>10} {'Baseline':>10}")
        print(f"  {'─'*42}")
        for fmt in ["binary", "ternary", "mcq"]:
            lllm_acc = comp["lllm"].get(fmt, {}).get("accuracy", None)
            base_acc = comp["baseline"].get(fmt, {}).get("accuracy", None)
            lllm_str = f"{lllm_acc*100:.1f}%" if lllm_acc is not None else "—"
            base_str = f"{base_acc*100:.1f}%" if base_acc is not None else "—"
            print(f"  {fmt+' accuracy':<20} {lllm_str:>10} {base_str:>10}")
        lllm_fir = comp["lllm"].get("fir", None)
        base_fir = comp["baseline"].get("fir", None)
        lllm_fir_str = f"{lllm_fir*100:.1f}%" if lllm_fir is not None else "—"
        base_fir_str = f"{base_fir*100:.1f}%" if base_fir is not None else "—"
        print(f"  {'FIR':<20} {lllm_fir_str:>10} {base_fir_str:>10}")

        comp_path = args.output.parent / "baseline_comparison.json"
        with open(comp_path, "w") as f:
            json.dump({"lllm": comp["lllm"], model_name: comp["baseline"]}, f, indent=2)
        print(f"\n  Comparison saved → {comp_path}")


if __name__ == "__main__":
    main()
