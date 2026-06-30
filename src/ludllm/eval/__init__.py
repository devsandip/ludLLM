"""The dimensional critique panel: an advisory coverage report per stage that
informs the human gate. Sits above the deterministic checks (authoring/checks.py)
and beside the prose stage's blocking critic (pipeline/writer/critique.py).
"""

from ludllm.eval.critique import (
    critique_chapter,
    critique_notes,
    critique_stage,
)
from ludllm.eval.rubric import STAGE_RUBRICS, derive_verdict, has_rubric

__all__ = [
    "critique_stage",
    "critique_chapter",
    "critique_notes",
    "has_rubric",
    "derive_verdict",
    "STAGE_RUBRICS",
]
