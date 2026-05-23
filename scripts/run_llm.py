"""
BioReasonCheck-FI · run_llm.py
Runs benchmark.jsonl against the L-LLM endpoint and saves model_outputs.jsonl.
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

load_dotenv(Path(__file__).parent.parent / ".env")

LLM_ENDPOINT_URL = os.getenv("HF_ENDPOINT_URL", "").rstrip("/") + "/v1/chat/completions"
LLM_API_TOKEN = os.getenv("HF_ACCESS_TOKEN", "")
MAX_TOKENS = 512
TEMPERATURE = 0.0  # deterministic for benchmark evaluation
_think_mode = False  # toggled by --think flag; off by default to avoid latency/timeouts


# ─────────────────────────── parsing helpers ──────────────────────────────────

def parse_binary(text: str) -> str:
    matches = re.findall(r"\b(yes|no)\b", text, re.IGNORECASE)
    if not matches:
        return "UNPARSEABLE"
    unique = {m.upper() for m in matches}
    if len(unique) == 1:
        return unique.pop()
    return "UNPARSEABLE"  # both YES and NO found


def parse_ternary(text: str) -> str:
    # Search in priority order: NOT_SUPPORTED before SUPPORTED to avoid substring match
    for label in ["NOT_SUPPORTED", "INSUFFICIENT_EVIDENCE", "SUPPORTED"]:
        if re.search(rf"\b{re.escape(label)}\b", text, re.IGNORECASE):
            return label.upper()
    return "UNPARSEABLE"


def parse_mcq(text: str, correct_option: str, gold_label: str) -> str:
    """Find standalone A/B/C/D near end of response and map to label."""
    # Check last 5 lines for a standalone letter answer
    lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
    search_text = "\n".join(lines[-5:]) if lines else text

    matches = re.findall(r"(?<![A-Za-z])([A-D])(?![A-Za-z])", search_text, re.IGNORECASE)
    if not matches:
        # Broaden to full text
        matches = re.findall(r"(?<![A-Za-z])([A-D])(?![A-Za-z])", text, re.IGNORECASE)
    if not matches:
        return "UNPARSEABLE"

    unique = {m.upper() for m in matches}
    if len(unique) > 1:
        return "UNPARSEABLE"

    chosen = unique.pop()
    return gold_label if chosen == correct_option else "NOT_" + gold_label if gold_label == "SUPPORTED" else "SUPPORTED"


def parse_response(entry: dict, raw_output: str) -> str:
    fmt = entry["format_type"]
    if fmt == "binary":
        return parse_binary(raw_output)
    if fmt == "ternary":
        return parse_ternary(raw_output)
    if fmt == "mcq":
        return parse_mcq(raw_output, entry["correct_option"], entry["gold_label"])
    return "UNPARSEABLE"


# ─────────────────────────── LLM call ────────────────────────────────────────

def call_llm(messages: list[dict], retries: int = 3) -> dict:
    """Returns {"content": str, "reasoning_content": str} or {"error": str}."""
    headers = {
        "Authorization": f"Bearer {LLM_API_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {
        "model": "longevity-llm",
        "messages": messages,
        "max_tokens": MAX_TOKENS,
        "temperature": TEMPERATURE,
        "chat_template_kwargs": {"enable_thinking": _think_mode},
    }

    for attempt in range(retries + 1):
        try:
            resp = requests.post(LLM_ENDPOINT_URL, headers=headers,
                                 json=payload, timeout=300)
            if resp.status_code == 429:
                if attempt < retries:
                    time.sleep(2)
                    continue
                return {"error": "ERROR:429"}
            resp.raise_for_status()
            msg = resp.json()["choices"][0]["message"]
            return {
                "content": msg.get("content") or "",
                "reasoning_content": msg.get("reasoning_content") or "",
            }
        except Exception as e:
            print(f"  [WARN] Attempt {attempt+1} failed: {e}")
            if attempt < retries:
                time.sleep(2)
    return {"error": "ERROR"}


# ─────────────────────────── main ────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Run benchmark against L-LLM endpoint")
    parser.add_argument("--input", type=Path,
                        default=Path(__file__).parent.parent / "data" / "processed" / "benchmark.jsonl")
    parser.add_argument("--output", type=Path,
                        default=Path(__file__).parent.parent / "outputs" / "model_outputs.jsonl")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print first 3 prompts without making API calls")
    parser.add_argument("--think", action="store_true",
                        help="Enable thinking mode (slow — only for reasoning trace collection)")
    parser.add_argument("--format-filter", default=None,
                        choices=["binary", "ternary", "mcq"],
                        help="Only run prompts of this format type")
    parser.add_argument("--split-filter", default=None,
                        choices=["train", "test"],
                        help="Only run prompts from this split")
    args = parser.parse_args()

    global _think_mode
    _think_mode = args.think
    if _think_mode:
        print("[INFO] Thinking mode ON — expect higher latency per call")

    # Startup check
    raw_url = os.getenv("HF_ENDPOINT_URL", "")
    raw_tok = os.getenv("HF_ACCESS_TOKEN", "")
    if not raw_url or not raw_tok:
        print("[ERROR] HF_ENDPOINT_URL or HF_ACCESS_TOKEN is not set. Check your .env file.")
        sys.exit(1)

    if not args.input.exists():
        print(f"[ERROR] Input file not found: {args.input}")
        sys.exit(1)

    entries = []
    with open(args.input, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))

    if args.format_filter:
        entries = [e for e in entries if e["format_type"] == args.format_filter]
    if args.split_filter:
        entries = [e for e in entries if e["split"] == args.split_filter]

    if args.dry_run:
        print(f"[DRY-RUN] {len(entries)} entries in {args.input}")
        for e in entries[:3]:
            print(f"\n--- {e['id']} ({e['format_type']}) ---")
            print(e["messages"][-1]["content"])
        return

    args.output.parent.mkdir(parents=True, exist_ok=True)

    results = []
    parse_ok = 0
    correct_count = 0

    def _verdict(parsed: str, entry: dict) -> str:
        if parsed == "UNPARSEABLE":
            return "UNPARSEABLE"
        fmt = entry["format_type"]
        correct = (parsed == entry["correct_answer"]) if fmt == "binary" else (parsed == entry["gold_label"])
        return "CORRECT" if correct else "WRONG"

    with open(args.output, "w", encoding="utf-8") as out_f:
        for i, entry in enumerate(entries):
            print(f"┌─ Prompt {i+1}/150 ─ {entry['id']} ({entry['format_type']}) ─ gene: {entry['gene']}")
            print(f"│  {entry['messages'][-1]['content'][:120].replace(chr(10), ' ')}")
            print(f"│  gold: {entry['gold_label']}")
            print(f"│  Posting...", end=" ", flush=True)
            result = call_llm(entry["messages"])
            is_error = "error" in result

            content = result.get("content", "")
            thinking_trace = result.get("reasoning_content", "")

            # Fallback: reasoning embedded inline as "{trace}</think>\n{answer}"
            if not thinking_trace and not is_error and "</think>" in content:
                import re as _re
                m = _re.search(r"(?:<think>)?(.*?)</think>(.*)", content, _re.DOTALL)
                if m:
                    thinking_trace = m.group(1).strip()
                    content = m.group(2).lstrip()

            raw_output = result.get("error", content)
            parsed = parse_response(entry, content) if not is_error else "UNPARSEABLE"
            verdict = _verdict(parsed, entry)

            if parsed != "UNPARSEABLE":
                parse_ok += 1
            if verdict == "CORRECT":
                correct_count += 1

            record = {
                "id": entry["id"],
                "fact_id": entry["fact_id"],
                "gene": entry["gene"],
                "format_type": entry["format_type"],
                "split": entry["split"],
                "gold_label": entry["gold_label"],
                "correct_answer": entry["correct_answer"],
                "correct_option": entry.get("correct_option", ""),
                "raw_output": raw_output,
                "thinking_trace": thinking_trace,
                "parsed_label": parsed,
            }
            out_f.write(json.dumps(record) + "\n")
            out_f.flush()
            results.append(record)

            # Per-prompt result
            status = {"CORRECT": "✓ CORRECT", "WRONG": "✗ WRONG", "UNPARSEABLE": "? UNPARSEABLE"}.get(verdict, "?")
            acc_so_far = correct_count / (i + 1) * 100
            print(f"   Got: {parsed:<28}  {status}  (accuracy so far: {acc_so_far:.0f}%)")
            print()

            # Batch summary every 10
            if (i + 1) % 10 == 0:
                acc = correct_count / (i + 1) * 100
                parse_rate = parse_ok / (i + 1) * 100
                print(f"  {'─'*80}")
                print(f"  Batch {(i+1)//10:2d} done | accuracy so far: {acc:.0f}%  "
                      f"parse rate: {parse_rate:.0f}%  ({i+1}/150 complete)")
                print(f"  {'─'*80}")

            if not is_error:
                time.sleep(1)

    total = len(results)
    print(f"\n[Done] {total} outputs → {args.output}")
    print(f"       Parse success rate: {parse_ok}/{total} ({parse_ok/total*100:.1f}%)")


if __name__ == "__main__":
    main()
