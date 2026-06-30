"""A novel project on disk: one folder under runs/, holding the canonical
book_state.json plus a subfolder per stage for the rendered markdown.

Layout:
    runs/<slug>/
        book_state.json          canonical, validated source of truth
        00_brief/                normalize output
        01_world/                world.md, ledger.md
        02_cast/                 cast.md
        03_structure/            structure.md
        04_outline/              outline.md
        05_manuscript/           chapter_NNN.md
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from ludllm.pipeline.stages import (
    STAGE_CAST,
    STAGE_DOSSIER,
    STAGE_NORMALIZE,
    STAGE_OUTLINE,
    STAGE_STRUCTURE,
    STAGE_WORLD,
)
from ludllm.state.schema import BookState, CreativeBrief, GenreProfile, ProjectMeta
from ludllm.state.store import load_state, save_state

STATE_FILE = "book_state.json"
MANUSCRIPT_DIR = "05_manuscript"

# Stage constant -> review subfolder. Order matters for display.
STAGE_DIRS: dict[str, str] = {
    STAGE_NORMALIZE: "00_brief",
    STAGE_WORLD: "01_world",
    STAGE_CAST: "02_cast",
    STAGE_STRUCTURE: "03_structure",
    STAGE_OUTLINE: "04_outline",
    STAGE_DOSSIER: "04b_dossiers",  # sorts between 04_outline and 05_manuscript
}


def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.strip().lower())
    return s.strip("-") or "untitled"


def next_auto_name(runs_dir: Path, today: date | None = None) -> str:
    """book_XXX_DD_MM_YY, where XXX increments across existing book_ folders."""
    today = today or date.today()
    nums = []
    if runs_dir.exists():
        for d in runs_dir.iterdir():
            m = re.match(r"book_(\d{3})_", d.name)
            if d.is_dir() and m:
                nums.append(int(m.group(1)))
    n = max(nums) + 1 if nums else 0
    return f"book_{n:03d}_{today.strftime('%d_%m_%y')}"


@dataclass
class NovelProject:
    root: Path

    @property
    def name(self) -> str:
        return self.root.name

    @property
    def state_path(self) -> Path:
        return self.root / STATE_FILE

    def stage_dir(self, stage: str) -> Path:
        return self.root / STAGE_DIRS[stage]

    @property
    def manuscript_dir(self) -> Path:
        return self.root / MANUSCRIPT_DIR

    def load(self) -> BookState:
        return load_state(self.state_path)

    def save(self, state: BookState) -> None:
        save_state(state, self.state_path)


def create_project(
    runs_dir: str | Path,
    premise: str,
    *,
    name: str | None = None,
    genre: GenreProfile | None = None,
    today: date | None = None,
) -> NovelProject:
    runs_dir = Path(runs_dir)
    folder = slugify(name) if name else next_auto_name(runs_dir, today)
    root = runs_dir / folder
    root.mkdir(parents=True, exist_ok=True)
    for sub in STAGE_DIRS.values():
        (root / sub).mkdir(exist_ok=True)
    (root / MANUSCRIPT_DIR).mkdir(exist_ok=True)

    state = BookState(
        meta=ProjectMeta(title=name or folder),
        genre=genre or GenreProfile(),
        brief=CreativeBrief(raw_input=premise),
    )
    project = NovelProject(root=root)
    project.save(state)
    # Seed the editable parameter file (a fully-commented template that overrides
    # nothing until the user uncomments a line, so the global file still applies).
    from ludllm.params import write_project_template

    write_project_template(root)
    return project


def open_project(root: str | Path) -> NovelProject:
    return NovelProject(root=Path(root))
