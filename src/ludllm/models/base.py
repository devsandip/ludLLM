"""Provider-agnostic model interface and the cross-family routing bundle.

The loop is written against `ChatModel` so a mock, Claude, Gemini, or GPT are
interchangeable. The `ModelBundle` makes the spec's model-heterogeneity explicit:
the drafter and the critic should be DIFFERENT families so the critic is not
grading its own homework.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

# Task tags let a mock branch deterministically. Real adapters ignore them.
TASK_DRAFT = "draft"
TASK_REVISE = "revise"
TASK_EXTRACT = "extract"
TASK_CRITIQUE = "critique"            # prose stage: blocking faults (leak/logic/repetition)
TASK_STAGE_CRITIQUE = "stage_critique"  # setup/prose dimensional panel: one dimension, scored
# Setup-stage tasks (the generators)
TASK_NORMALIZE = "normalize"
TASK_WORLD = "world"
TASK_CAST = "cast"
TASK_STRUCTURE = "structure"
TASK_OUTLINE = "outline"
TASK_DOSSIER = "dossier"        # per-character intelligence dossier (between outline and the writer)


@runtime_checkable
class ChatModel(Protocol):
    name: str
    family: str  # "anthropic" | "google" | "openai" | "mock"

    def generate(
        self, *, system: str, prompt: str, task: str | None = None, max_tokens: int = 2048
    ) -> str:
        ...


@dataclass
class ModelBundle:
    """The models the pipeline routes to. Drafter and critic should differ in
    family; the spec calls the generator/critic split the core quality unlock.
    `author` is the strong model the setup generators use; it falls back to the
    drafter when not set."""

    drafter: ChatModel
    extractor: ChatModel
    critic: ChatModel
    author: ChatModel | None = None

    @property
    def author_model(self) -> ChatModel:
        return self.author or self.drafter

    def assert_cross_family_critique(self) -> None:
        if self.drafter.family == self.critic.family and self.drafter.family != "mock":
            raise ValueError(
                "critic shares a family with the drafter; cross-family critique is "
                "the point. Use a different provider for the critic."
            )
