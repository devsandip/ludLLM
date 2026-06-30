"""The runtime `--interactive` prompt: at the start of a stage, show the params
relevant to THAT stage, let the user change them, persist any change to the
per-project params.toml, and return the resolved Params.

This is the runtime half of "ask before each stage". The other half is Claude
driving the pipeline conversationally (it reads `ludllm params`, asks, and writes
the same file). Both edit one shared source of truth, so they agree.

Non-interactive callers never touch this; the runtime reads params silently.
"""

from __future__ import annotations

import sys
from typing import TextIO

from ludllm.params import (
    Params,
    coerce,
    get_value,
    load_params,
    relevant_specs,
    set_project_value,
)


def prompt_stage_params(
    project_dir,
    stage: str,
    *,
    inp: TextIO | None = None,
    out: TextIO | None = None,
) -> Params:
    """Confirm or change the immediate stage's params, then return resolved Params.

    Press Enter to keep a value; type a new one to change it (validated, then
    written to the per-project file). A non-tty / EOF leaves everything untouched.
    """
    inp = inp or sys.stdin
    out = out or sys.stdout
    specs = relevant_specs(stage)
    params = load_params(project_dir)
    if not specs:
        return params

    print(f"\nParameters for the '{stage}' stage (Enter keeps the current value):", file=out)
    for spec in specs:
        current = get_value(params, spec.key)
        hint = f" [{'|'.join(spec.choices)}]" if spec.choices else ""
        print(f"\n  {spec.key}{hint}", file=out)
        print(f"    {spec.desc}", file=out)
        out.write(f"    {spec.key} = {current}  -> ")
        out.flush()
        line = inp.readline()
        if line == "":  # EOF / non-tty: stop asking, keep the rest as-is
            break
        raw = line.strip()
        if not raw:
            continue
        try:
            value = coerce(spec, raw)
        except ValueError as exc:
            print(f"    kept {current} ({exc})", file=out)
            continue
        set_project_value(project_dir, spec.key, value)
        print(f"    set {spec.key} = {value}", file=out)

    return load_params(project_dir)
