"""Ensure prompts don't exceed 30K tokens (cl100k_base)."""
import tiktoken
from config import MAX_TOKENS, TOKENIZER_ENCODING

_enc = tiktoken.get_encoding(TOKENIZER_ENCODING)


def count_tokens(text: str) -> int:
    return len(_enc.encode(text))


def is_within_limit(text: str) -> bool:
    return count_tokens(text) <= MAX_TOKENS


def truncate_to_limit(text: str) -> str:
    tokens = _enc.encode(text)
    if len(tokens) <= MAX_TOKENS:
        return text
    return _enc.decode(tokens[:MAX_TOKENS])
