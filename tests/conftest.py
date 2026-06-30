"""Test isolation: pin the global params file to a nonexistent path so the suite
never reads a real ~/.config/ludllm/params.toml on the dev machine. Per-test
fixtures can still point LUDLLM_PARAMS at a file they write."""

from __future__ import annotations

import pytest

from ludllm.params import GLOBAL_ENV


@pytest.fixture(autouse=True)
def _isolate_global_params(tmp_path_factory, monkeypatch):
    missing = tmp_path_factory.mktemp("no_global") / "params.toml"
    monkeypatch.setenv(GLOBAL_ENV, str(missing))
