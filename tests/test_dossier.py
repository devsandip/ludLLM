"""The dossier stage: principal selection, ledger-bound redactions, and a
graceful offline artifact build (no image backend, placeholder photo)."""

from __future__ import annotations

import json
import shutil

from ludllm.models.base import ModelBundle
from ludllm.models.mock import MockModel
from ludllm.pipeline.dossier import (
    build_dossier_artifacts,
    character_secrets,
    generate_dossiers,
    principals,
)
from ludllm.state.schema import BookState, Belief, Character, Fact

_CANNED = json.dumps({
    "appearance": "a woman in her thirties, South Indian, plain, watchful",
    "stamp": "ACTIVE",
    "cover_rows": [["NAME", "Asha Rao"], ["TRUE NAME", "x"], ["STATUS", "ACTIVE"]],
    "redacted_cover": ["TRUE NAME"],
    "sections": [["BACKGROUND", "Recruited young."], ["PROFILE", "Disciplined."]],
    "sealed": [["TRUE ORIGIN", "f_switch"]],
    "associates": ["HANDLER ...... K"],
    "training": "Tradecraft.",
    "capabilities": "Surveillance.",
    "oplog": ["2019 recruited"],
    "oplog_sealed_label": "TRUE ROLE",
    "threat": "THREAT LEVEL - LOW",
    "threat_detail": "Monitor.",
    "standing_orders": "Run as normal.",
    "authoriser": "AUTHORISED: Chief",
})


class _CannedAuthor:
    name = "canned"
    family = "anthropic"

    def generate(self, *, system: str, prompt: str, task: str | None = None, max_tokens: int = 2048) -> str:
        return _CANNED


def _bundle() -> ModelBundle:
    return ModelBundle(drafter=MockModel(), extractor=MockModel(),
                       critic=MockModel(family="google"), author=_CannedAuthor())


def _state() -> BookState:
    s = BookState()
    s.authored.world.setting = "A cold-war intelligence service"
    s.authored.characters = [
        Character(id="c_asha", name="Asha Rao", role="Protagonist", born=1990,
                  initial_beliefs=[Belief(fact_id="f_switch", kind="falsely_believes",
                                          false_value="She is an orphan.")]),
        Character(id="c_bose", name="Bose", role="Functionary clerk"),
    ]
    s.authored.facts = [
        Fact(id="f_switch", text="Asha Rao was switched at birth by the service.", tier="hidden"),
        Fact(id="f_open", text="The service exists.", tier="public"),
    ]
    return s


def test_principals_drops_pure_functionary():
    ids = {c.id for c in principals(_state())}
    assert ids == {"c_asha"}


def test_secrets_bind_to_the_ledger():
    s = _state()
    secs = dict(character_secrets(s, s.authored.characters[0]))
    assert "f_switch" in secs       # hidden + names the subject
    assert "f_open" not in secs     # public facts are never sealed


def test_generate_seals_every_secret():
    s = _state()
    generate_dossiers(s, _bundle())
    assert len(s.authored.dossiers) == 1
    d = s.authored.dossiers[0]
    assert d.character_id == "c_asha"
    assert "f_switch" in {fid for _, fid in d.sealed}


def test_build_artifacts_offline(tmp_path, monkeypatch):
    monkeypatch.setenv("LUDLLM_NO_IMAGES", "1")
    s = _state()
    generate_dossiers(s, _bundle())
    written = build_dossier_artifacts(s, tmp_path)
    if shutil.which("rsvg-convert"):
        assert any(p.endswith(".pdf") for p in written)
        assert s.authored.dossiers[0].pdf_path
    else:
        assert written == []
