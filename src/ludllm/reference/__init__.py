"""Bundled reference data the setup stages draw on (not model output).

Currently: a curated catalogue of spy-genre tropes the structure stage selects
from under a principled-use rule. Reference data lives here so it is versioned
and auditable, separate from prompts.py (instructions) and schema.py (shapes).
"""

from ludllm.reference.tropes import SPY_TROPES, tropes_digest

__all__ = ["SPY_TROPES", "tropes_digest"]
