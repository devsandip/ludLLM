"""User-editable pipeline parameters: the loop and revision tunables, in a file
the showrunner can edit instead of code constants.

These are the knobs the loop/revision audit surfaced: how many revise passes a
chapter gets, how many transient-fault retries, whether the per-chapter advisory
note runs, what the dimensional critique does with its verdict, whether it runs
at all, and how many auto-revise passes a setup stage gets.

Precedence (lowest wins to highest):
  1. package defaults  -> the Pydantic model defaults in this file
  2. global file       -> $LUDLLM_PARAMS, else ~/.config/ludllm/params.toml
  3. per-project file  -> <project>/params.toml

A stage reads ONLY the params relevant to it (see STAGE_PARAMS). The runtime
reads the resolved file silently and never blocks; `--interactive` (and Claude,
when it drives the pipeline conversationally) asks the user to confirm or change
the immediate stage's params before running, writing any change to the
per-project file.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from ludllm.state.schema import CritiqueMode

GLOBAL_ENV = "LUDLLM_PARAMS"
PROJECT_FILE = "params.toml"


# --------------------------------------------------------------------------- #
# The parameter model (also the package-default floor)
# --------------------------------------------------------------------------- #

class CritiqueParams(BaseModel):
    """The dimensional critique panel on the setup stages (world/cast/structure/outline)."""

    mode: CritiqueMode = CritiqueMode.auto_revise
    enabled: bool = True
    auto_revise_passes: int = Field(default=1, ge=0, le=5)


class WriterParams(BaseModel):
    """The per-chapter writer loop (Stage 5) and the full-book runner."""

    max_revise: int = Field(default=2, ge=0, le=10)
    retries: int = Field(default=3, ge=0, le=10)
    advisory: bool = True


class Params(BaseModel):
    critique: CritiqueParams = Field(default_factory=CritiqueParams)
    writer: WriterParams = Field(default_factory=WriterParams)


# --------------------------------------------------------------------------- #
# Which params are relevant to which stage (the "only the immediate stage" rule)
# --------------------------------------------------------------------------- #

_CRITIQUE_KEYS = ["critique.mode", "critique.enabled", "critique.auto_revise_passes"]
_WRITER_KEYS = ["writer.max_revise", "writer.retries", "writer.advisory"]

# Stage -> the dotted param keys to surface when running that stage. normalize and
# dossier have no loop/revision tunables, so they prompt nothing.
STAGE_PARAMS: dict[str, list[str]] = {
    "world": _CRITIQUE_KEYS,
    "cast": _CRITIQUE_KEYS,
    "structure": _CRITIQUE_KEYS,
    "outline": _CRITIQUE_KEYS,
    "writer": _WRITER_KEYS,
}


@dataclass(frozen=True)
class ParamSpec:
    key: str               # dotted, e.g. "critique.mode"
    kind: str              # "enum" | "bool" | "int"
    desc: str
    choices: tuple[str, ...] = ()
    minimum: int | None = None
    maximum: int | None = None


PARAM_SPECS: dict[str, ParamSpec] = {
    "critique.mode": ParamSpec(
        "critique.mode", "enum",
        "what the critique does with its verdict: advisory_only score-only; "
        "auto_revise regenerates if not 'ship'; blocking holds the freeze on 'regenerate'",
        choices=tuple(m.value for m in CritiqueMode),
    ),
    "critique.enabled": ParamSpec(
        "critique.enabled", "bool", "run the dimensional critique panel on this stage at all",
    ),
    "critique.auto_revise_passes": ParamSpec(
        "critique.auto_revise_passes", "int",
        "max auto_revise regenerations when the verdict is not 'ship' (0 = score but never regenerate)",
        minimum=0, maximum=5,
    ),
    "writer.max_revise": ParamSpec(
        "writer.max_revise", "int",
        "max draft->critique->revise passes per chapter before it stops",
        minimum=0, maximum=10,
    ),
    "writer.retries": ParamSpec(
        "writer.retries", "int", "transient-fault retries per chapter on the full-book run",
        minimum=0, maximum=10,
    ),
    "writer.advisory": ParamSpec(
        "writer.advisory", "bool", "run the per-chapter advisory coverage note on accepted prose",
    ),
}


def relevant_specs(stage: str) -> list[ParamSpec]:
    return [PARAM_SPECS[k] for k in STAGE_PARAMS.get(stage, [])]


# --------------------------------------------------------------------------- #
# Loading and merging the layers
# --------------------------------------------------------------------------- #

def global_params_path() -> Path:
    env = os.environ.get(GLOBAL_ENV)
    if env:
        return Path(env).expanduser()
    return Path.home() / ".config" / "ludllm" / PROJECT_FILE


def project_params_path(project_dir: str | Path) -> Path:
    return Path(project_dir) / PROJECT_FILE


def _read_toml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("rb") as f:
        return tomllib.load(f)


def _deep_merge(base: dict, over: dict) -> dict:
    out = dict(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def load_params(project_dir: str | Path | None = None) -> Params:
    """Merge package defaults <- global <- per-project and validate."""
    data: dict[str, Any] = {}
    data = _deep_merge(data, _read_toml(global_params_path()))
    if project_dir is not None:
        data = _deep_merge(data, _read_toml(project_params_path(project_dir)))
    return Params.model_validate(data)


# --------------------------------------------------------------------------- #
# Reading / writing individual values (for the interactive prompt and Claude)
# --------------------------------------------------------------------------- #

def get_value(params: Params, key: str) -> Any:
    section, name = key.split(".", 1)
    val = getattr(getattr(params, section), name)
    return val.value if isinstance(val, CritiqueMode) else val


def coerce(spec: ParamSpec, raw: str) -> Any:
    """Parse a string from the user/file into the typed, validated value."""
    raw = raw.strip()
    if spec.kind == "bool":
        if raw.lower() in ("true", "t", "yes", "y", "1", "on"):
            return True
        if raw.lower() in ("false", "f", "no", "n", "0", "off"):
            return False
        raise ValueError(f"{spec.key}: expected true/false, got {raw!r}")
    if spec.kind == "int":
        try:
            n = int(raw)
        except ValueError as exc:
            raise ValueError(f"{spec.key}: expected an integer, got {raw!r}") from exc
        if spec.minimum is not None and n < spec.minimum:
            raise ValueError(f"{spec.key}: must be >= {spec.minimum}")
        if spec.maximum is not None and n > spec.maximum:
            raise ValueError(f"{spec.key}: must be <= {spec.maximum}")
        return n
    if spec.kind == "enum":
        if raw not in spec.choices:
            raise ValueError(f"{spec.key}: must be one of {', '.join(spec.choices)}")
        return raw
    raise ValueError(f"unknown param kind {spec.kind!r}")


def _toml_scalar(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    return '"' + str(v).replace("\\", "\\\\").replace('"', '\\"') + '"'


def _dump_toml(data: dict[str, dict[str, Any]]) -> str:
    lines = [
        "# LudLLM per-project parameter overrides. Anything set here overrides the",
        "# global file (~/.config/ludllm/params.toml) and the package defaults.",
        "# See `ludllm params <project>` for the resolved values and their sources.",
        "",
    ]
    for section in ("critique", "writer"):
        vals = data.get(section)
        if not isinstance(vals, dict) or not vals:
            continue
        lines.append(f"[{section}]")
        for k, v in vals.items():
            lines.append(f"{k} = {_toml_scalar(v)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def set_project_value(project_dir: str | Path, key: str, value: Any) -> None:
    """Read-modify-write the per-project params.toml, setting one dotted key.

    Validates by round-tripping the whole file through the Params model. Drops any
    comments the file had; the documented template lives in the global file."""
    path = project_params_path(project_dir)
    data = _read_toml(path)
    section, name = key.split(".", 1)
    data.setdefault(section, {})[name] = value
    Params.model_validate(data)  # reject an illegal combination before persisting
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_dump_toml(data), encoding="utf-8")


# --------------------------------------------------------------------------- #
# Templates and source inspection
# --------------------------------------------------------------------------- #

def template_text() -> str:
    """A fully-commented template: every tunable shown at its default, all inert.

    Seeded into a new project (overrides nothing until you uncomment a line) and
    written to the global path by `ludllm params --init-global` (edit there to set
    cross-book defaults)."""
    d = Params()  # defaults
    return (
        "# LudLLM pipeline parameters. Every line is commented out, so this file\n"
        "# overrides nothing as shipped. Uncomment a line to change that knob.\n"
        "# Precedence: per-project params.toml > global ~/.config/ludllm/params.toml > defaults.\n"
        "\n"
        "[critique]  # the dimensional panel on world / cast / structure / outline\n"
        f"# mode = \"{d.critique.mode.value}\"          "
        "# advisory_only | auto_revise | blocking\n"
        f"# enabled = {str(d.critique.enabled).lower()}            # run the panel at all\n"
        f"# auto_revise_passes = {d.critique.auto_revise_passes}    "
        "# regenerations when verdict != ship (0 = never)\n"
        "\n"
        "[writer]  # the per-chapter writer loop (Stage 5) and the full-book runner\n"
        f"# max_revise = {d.writer.max_revise}          # max draft->critique->revise passes per chapter\n"
        f"# retries = {d.writer.retries}             # transient-fault retries per chapter\n"
        f"# advisory = {str(d.writer.advisory).lower()}         # per-chapter advisory coverage note\n"
    )


def write_project_template(project_dir: str | Path, *, overwrite: bool = False) -> Path:
    path = project_params_path(project_dir)
    if path.exists() and not overwrite:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(template_text(), encoding="utf-8")
    return path


def write_global_template(*, overwrite: bool = False) -> Path:
    path = global_params_path()
    if path.exists() and not overwrite:
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(template_text(), encoding="utf-8")
    return path


def resolve_with_sources(project_dir: str | Path | None = None) -> list[dict[str, Any]]:
    """For each known param: its resolved value and which layer set it
    (default | global | project). Drives `ludllm params` and Claude's read."""
    g = _read_toml(global_params_path())
    p = _read_toml(project_params_path(project_dir)) if project_dir is not None else {}
    resolved = load_params(project_dir)
    rows = []
    for key, spec in PARAM_SPECS.items():
        section, name = key.split(".", 1)
        if name in p.get(section, {}):
            source = "project"
        elif name in g.get(section, {}):
            source = "global"
        else:
            source = "default"
        rows.append({"key": key, "value": get_value(resolved, key), "source": source, "spec": spec})
    return rows
