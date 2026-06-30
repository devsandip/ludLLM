"""Deterministic, model-independent guards. The leak guard is the load-bearing
one: the primer says it "stays useful regardless of model."

This v1 detects a leak by substring match against a forbidden fact's text. Real
prose leaks are paraphrased, so the production guard will need semantic matching
(an NLI pass or a cheap model) on top of this exact-match floor. The exact-match
layer stays as a cheap first line.
"""

from __future__ import annotations

from ludllm.state.schema import Fact


def _mentions(text: str, fact: Fact) -> bool:
    needle = fact.text.rstrip(".").lower()
    return needle in text.lower()


def find_leaks(text: str, forbidden: list[Fact]) -> list[str]:
    """Return the ids of forbidden facts that surface in `text`."""
    return [f.id for f in forbidden if _mentions(text, f)]
