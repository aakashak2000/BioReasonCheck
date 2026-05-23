"""Client for querying the hosted L-LLM HuggingFace endpoint."""
import re
import requests
from config import HF_ENDPOINT_URL, HF_ACCESS_TOKEN


def query_lllm(prompt: str, system: str = "", max_new_tokens: int = 512,
               think: bool = False, temperature: float = 0.0) -> dict:
    """
    Send a prompt to L-LLM and return:
      'response'       — final answer
      'thinking_trace' — chain-of-thought (empty if think=False)
    """
    headers = {
        "Authorization": f"Bearer {HF_ACCESS_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": "longevity-llm",
        "messages": messages,
        "max_tokens": max_new_tokens,
        "temperature": temperature,
        "chat_template_kwargs": {"enable_thinking": think},
    }

    url = HF_ENDPOINT_URL.rstrip("/") + "/v1/chat/completions"
    response = requests.post(url, headers=headers, json=payload, timeout=300)
    response.raise_for_status()

    msg = response.json()["choices"][0]["message"]
    content = msg.get("content") or ""
    thinking_trace = msg.get("reasoning_content") or ""

    # Fallback: reasoning embedded inline as "{trace}</think>\n{answer}"
    if not thinking_trace and "</think>" in content:
        m = re.search(r"(?:<think>)?(.*?)</think>(.*)", content, re.DOTALL)
        if m:
            thinking_trace = m.group(1).strip()
            content = m.group(2).lstrip()

    return {"response": content.strip(), "thinking_trace": thinking_trace}
