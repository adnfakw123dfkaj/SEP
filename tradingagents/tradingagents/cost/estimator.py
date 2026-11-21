"""Deterministic, network-free token estimation for budget routing.

The estimator is deliberately a conservative approximation, not a provider
tokenizer: it is used to choose a route before a call, while final cost comes
from provider-reported usage.  CJK characters count as one token each; runs
of ASCII word characters count as one token; punctuation is counted
separately.  This keeps estimates stable across providers and test runs.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from tradingagents.contracts.cost import TokenEstimate

_KNOWN_MODELS = frozenset({"deepseek-flash", "deepseek-v4-pro"})

_CJK = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
_ASCII_WORD = re.compile(r"[A-Za-z0-9_]+")
_OTHER_SYMBOL = re.compile(r"[^\w\s]", re.UNICODE)

_DEFAULT_OUTPUT_CAP = 4096


def _as_text(messages: str | Sequence[str]) -> str:
    if isinstance(messages, str):
        return messages
    return "\n".join(str(message) for message in messages)


def _count_tokens(text: str) -> int:
    if not text.strip():
        return 0
    cjk = len(_CJK.findall(text))
    without_cjk = _CJK.sub(" ", text)
    words = len(_ASCII_WORD.findall(without_cjk))
    symbols = len(_OTHER_SYMBOL.findall(without_cjk))
    return cjk + words + symbols


def estimate_tokens(
    messages: str | Sequence[str],
    model: str,
    *,
    max_output_tokens: int | None = None,
) -> TokenEstimate:
    """Estimate input/output tokens for a prospective call.

    ``max_output_tokens`` is a hard cap when supplied.  Empty input returns a
    zero estimate rather than a synthetic minimum, so callers can distinguish
    "nothing to send" from a real prompt.
    """
    text = _as_text(messages)
    input_tokens = _count_tokens(text)

    if input_tokens == 0:
        return TokenEstimate(
            input_tokens=0,
            output_tokens=0,
            total_tokens=0,
            confidence="low",
        )

    output_tokens = max(1, min(_DEFAULT_OUTPUT_CAP, input_tokens // 4))
    if max_output_tokens is not None:
        output_tokens = min(output_tokens, max(0, max_output_tokens))

    return TokenEstimate(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        confidence="medium" if model in _KNOWN_MODELS else "low",
    )
