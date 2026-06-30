"""Deterministic stand-in models for engine-first development.

`MockModel` lets the full chapter loop run with no API calls and no cost, so the
orchestration (scoped-context assembly, no-leak guard, gate convergence, state
write-back) is proven before any real generator is wired in. It is well-behaved:
it only emits facts it was handed, so it never leaks on its own.

`LeakyMockModel` simulates a generator that knows something it should not and
spills it. It is used in tests to prove the leak guard has teeth.
"""

from __future__ import annotations

import json

from ludllm.models.base import (
    TASK_CRITIQUE,
    TASK_DRAFT,
    TASK_EXTRACT,
    TASK_REVISE,
    TASK_STAGE_CRITIQUE,
)
from ludllm.util.blocks import read_block


class MockModel:
    def __init__(self, name: str = "mock", family: str = "mock", critique_score: int = 4) -> None:
        self.name = name
        self.family = family
        self.critique_score = critique_score  # the score the dimensional panel returns

    def _leak_suffix(self) -> str:
        return ""

    def generate(
        self, *, system: str, prompt: str, task: str | None = None, max_tokens: int = 2048
    ) -> str:
        if task in (TASK_DRAFT, TASK_REVISE):
            return self._draft(prompt, revising=(task == TASK_REVISE))
        if task == TASK_EXTRACT:
            return self._extract(prompt)
        if task == TASK_CRITIQUE:
            return json.dumps({"flags": []})
        if task == TASK_STAGE_CRITIQUE:
            dim = read_block(prompt, "DIMENSION") or "dimension"
            return json.dumps(
                {"score": self.critique_score, "evidence": f"(mock {dim})", "fix": "(mock fix)"}
            )
        # default: echo the beat
        return read_block(prompt, "BEAT")

    def _draft(self, prompt: str, *, revising: bool) -> str:
        beat = read_block(prompt, "BEAT")
        allowed = read_block(prompt, "ALLOWED_FACTS")
        lines = [f"The chapter turned on this: {beat}."]
        for fact_line in [ln for ln in allowed.splitlines() if ln.strip()]:
            # fact_line looks like "- <id>: <text>"
            text = fact_line.split(":", 1)[-1].strip()
            if text:
                lines.append(f"On the page, it held that {text}")
        if revising:
            flags = read_block(prompt, "FLAGS")
            lines.append(f"The draft was tightened to address: {flags}.")
        return "\n".join(lines) + self._leak_suffix()

    def _extract(self, prompt: str) -> str:
        # The well-behaved extractor reflects the chapter's planned character
        # reveals as facts the POV has now learned.
        planned = read_block(prompt, "PLANNED_CHARACTER_REVEALS")
        learned = [x.strip() for x in planned.split(",") if x.strip()]
        summary = read_block(prompt, "INTENT") or read_block(prompt, "BEAT")
        return json.dumps(
            {"learned_fact_ids": learned, "established_fact_ids": learned, "summary": summary}
        )


class LeakyMockModel(MockModel):
    """A drafter that spills a secret it was never supposed to have."""

    def __init__(self, leak_text: str, name: str = "leaky", family: str = "mock") -> None:
        super().__init__(name=name, family=family)
        self.leak_text = leak_text

    def _leak_suffix(self) -> str:
        return f"\nUnknown to the page's logic, {self.leak_text}"


class ScriptedAuthorModel:
    """A setup-stage author that returns canned JSON per task. Stands in for a
    real generator so the generator scaffolding (parse, validate, freeze) can be
    tested deterministically."""

    def __init__(self, responses: dict[str, str], name: str = "scripted", family: str = "mock"):
        self.responses = responses
        self.name = name
        self.family = family

    def generate(
        self, *, system: str, prompt: str, task: str | None = None, max_tokens: int = 2048
    ) -> str:
        if task not in self.responses:
            raise KeyError(f"ScriptedAuthorModel has no canned response for task {task!r}")
        return self.responses[task]
