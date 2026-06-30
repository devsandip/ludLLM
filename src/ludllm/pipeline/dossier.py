"""The dossier stage: a per-character classified intelligence file, generated
between the outline (Stage 4) and the writer (Stage 5).

Two halves:
  generate_dossiers     model-driven. For each principal it writes the file's text
                        (cover fields, background, training, ops) and, crucially,
                        the `sealed` redactions BOUND TO THE LEDGER: every secret
                        the in-world readership is not cleared to know becomes a
                        blacked-out line, so an un-redacted file reads as the
                        novel's reveals. Pure (state + model); testable with mocks.
  build_dossier_artifacts  side-effecting. Generates a surveillance portrait per
                        subject (region/class/profession matched, never defaulting
                        to a Western look), composes a three-page document with the
                        file's REAL text over the photo and paper, and rasterizes a
                        PDF plus a side-by-side spread. Degrades gracefully: with no
                        image backend it draws a placeholder photo; with no
                        rsvg-convert it writes nothing and leaves the data in state.

The split mirrors the rest of the pipeline: generators mutate state, artifacts are
produced from that state. Image generation is the only paid, non-deterministic
part and is guarded (LUDLLM_NO_IMAGES skips it).
"""

from __future__ import annotations

import base64
import html
import io
import json
import os
import shutil
import subprocess
import tempfile
import textwrap
from pathlib import Path

from ludllm.models.base import TASK_DOSSIER, ModelBundle
from ludllm.prompts import DOSSIER_SYSTEM
from ludllm.state.schema import BookState, Character, Dossier
from ludllm.util.blocks import make_block
from ludllm.util.jsonio import loads_lenient

_SECRET_TIERS = {"hidden", "delayed", "never_explicit"}

# ----------------------------------------------------------------------------- #
# Stage 1: generate the dossier content (model-driven, ledger-bound redactions)
# ----------------------------------------------------------------------------- #


def _looks_functionary(c: Character) -> bool:
    return c.role.strip().lower().startswith("functionary")


def _first_name(c: Character) -> str:
    return (c.name or "").split()[0] if c.name else ""


def principals(state: BookState) -> list[Character]:
    """The load-bearing roster: every named character except pure functionaries,
    plus any functionary who is a POV or is written into a fact (so the cast's
    spear-carriers do not each get a file, but anyone who matters does)."""
    povs = {cb.pov for cb in state.authored.chapter_outline if cb.pov}
    out = []
    for c in state.authored.characters:
        name = _first_name(c).lower()
        mentioned = bool(name) and any(name in f.text.lower() for f in state.authored.facts)
        if c.id in povs or mentioned or not _looks_functionary(c):
            out.append(c)
    return out


def character_secrets(state: BookState, c: Character, cap: int = 5) -> list[tuple[str, str]]:
    """The secret facts that should be redacted on this character's file: secrets
    ABOUT them (the fact names them) and secrets KEPT FROM them (they do_not_know
    or falsely_believe a hidden/delayed fact). This is what ties the redactions to
    the reveal ledger."""
    name = _first_name(c).lower()
    belief = {b.fact_id: b.kind.value for b in c.initial_beliefs}
    seen: set[str] = set()
    about: list[tuple[str, str]] = []
    keptfrom: list[tuple[str, str]] = []
    for f in state.authored.facts:
        if f.tier.value not in _SECRET_TIERS or f.id in seen:
            continue
        if name and name in f.text.lower():
            about.append((f.id, f.text))
            seen.add(f.id)
        elif belief.get(f.id) in ("does_not_know", "falsely_believes"):
            keptfrom.append((f.id, f.text))
            seen.add(f.id)
    return (about + keptfrom)[:cap]


def _fileno(c: Character, i: int) -> str:
    tag = "".join(ch for ch in (c.name or c.id).upper() if ch.isalpha())[:1] or "X"
    return f"RAW/FILE/{tag}-{i + 1:03d}"


def _dossier_from(data: dict, c: Character, secrets: list[tuple[str, str]], i: int) -> Dossier:
    """Build a validated Dossier from tolerant model output, guaranteeing every
    handed-in secret ends up as a sealed redaction even if the model dropped one."""
    sealed = [s for s in data.get("sealed", []) if isinstance(s, list) and len(s) == 2]
    covered = {fid for _, fid in sealed}
    for fid, _ in secrets:
        if fid not in covered:
            sealed.append(["RESTRICTED", fid])
    return Dossier(
        character_id=c.id,
        name=data.get("name") or c.name,
        codename=data.get("codename") or (c.name or c.id).upper(),
        fileno=_fileno(c, i),
        stamp=str(data.get("stamp") or "CLASSIFIED")[:18],
        appearance=data.get("appearance", ""),
        photocap=data.get("photocap", "SURVEILLANCE"),
        cover_rows=[r for r in data.get("cover_rows", []) if isinstance(r, list) and len(r) == 2],
        redacted_cover=[str(x) for x in data.get("redacted_cover", [])],
        sections=[s for s in data.get("sections", []) if isinstance(s, list) and len(s) == 2],
        sealed=sealed,
        associates=[str(x) for x in data.get("associates", [])],
        training=data.get("training", ""),
        capabilities=data.get("capabilities", ""),
        oplog=[str(x) for x in data.get("oplog", [])],
        oplog_sealed_label=data.get("oplog_sealed_label", "RESTRICTED FINDING"),
        threat=data.get("threat", "THREAT LEVEL - UNDER REVIEW"),
        threat_detail=data.get("threat_detail", ""),
        standing_orders=data.get("standing_orders", ""),
        authoriser=data.get("authoriser", "AUTHORISED: case authority"),
    )


def generate_dossiers(state: BookState, models: ModelBundle, notes: str = "") -> None:
    w = state.authored.world
    world_block = json.dumps({
        "setting": w.setting,
        "eras": [{"label": e.label, "year_start": e.year_start, "year_end": e.year_end, "place": e.place}
                 for e in w.eras],
    })
    dossiers: list[Dossier] = []
    for i, c in enumerate(principals(state)):
        secrets = character_secrets(state, c)
        blocks = [
            make_block("SUBJECT", json.dumps({
                "name": c.name, "role": c.role, "born": c.born,
                "backstory": c.backstory, "worldview": c.worldview})),
            make_block("WORLD", world_block),
            make_block("SECRETS", json.dumps([{"fact_id": fid, "text": txt} for fid, txt in secrets])),
        ]
        if notes:
            blocks.append(make_block("REVISION_NOTES", notes))
        prompt = "\n".join(blocks)
        # Resilience: one character's malformed JSON must not sink the batch. Retry
        # the generate+parse a few times, then fall back to a minimal valid file
        # (the ledger-bound redactions are forced in regardless of the model text).
        data: dict | None = None
        for _ in range(3):
            try:
                raw = models.author_model.generate(
                    system=DOSSIER_SYSTEM, prompt=prompt, task=TASK_DOSSIER, max_tokens=4000,
                )
                data = loads_lenient(raw)
                break
            except Exception:  # noqa: BLE001 - bad model output or transient fault; retry
                continue
        dossiers.append(_dossier_from(data or {}, c, secrets, i))
    state.authored.dossiers = dossiers


# ----------------------------------------------------------------------------- #
# Stage 2: compose the artifacts (portrait + 3-page PDF + side-by-side spread)
# ----------------------------------------------------------------------------- #

_MONO = "Courier, monospace"
_SANS = "Helvetica, Arial, sans-serif"
_HEAVY = "Arial Black, Helvetica, sans-serif"
_INK, _SEP, _RED, _BLK = "#2a2118", "#6e4a2c", "#9b2222", "#1a160f"
_W, _H, _LX, _RX = 800, 1220, 56, 744

_PORTRAIT_TPL = (
    "A grainy high-contrast black-and-white CCTV security-camera photograph, head and shoulders, of {look}. "
    "The person's ethnicity, age and class MUST match that description exactly; do NOT default to a European, "
    "Caucasian, or generic Western look. Plain dark neutral background, low-resolution surveillance feel. No text, "
    "no watermark, no timestamp. Fictional person, not any real public figure."
)
_PAPER_PROMPT = (
    "A blank sheet of aged cream archival paper, lightly worn, evenly and softly lit, subtle age toning and a few "
    "faint stains near the edges, no deep shadows, filling the frame. Absolutely no text, no writing, no letters, "
    "no photographs - only the empty aged paper."
)


def _gen_image(prompt: str, size: str = "1024x1024") -> bytes | None:
    if os.environ.get("LUDLLM_NO_IMAGES"):
        return None
    try:
        from openai import OpenAI
        c = OpenAI()
        r = c.images.generate(
            model=os.environ.get("LUDLLM_IMAGE_MODEL", "gpt-image-1"),
            prompt=prompt, size=size, quality="medium", n=1,
        )
        return base64.b64decode(r.data[0].b64_json)
    except Exception:
        return None


def _to_jpeg_b64(png: bytes, longest: int) -> str:
    from PIL import Image
    im = Image.open(io.BytesIO(png)).convert("RGB")
    im.thumbnail((longest, longest))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=74)
    return base64.b64encode(buf.getvalue()).decode()


def _esc(s: object) -> str:
    return html.escape(str(s), quote=False)


def _wrap(t: str, n: int) -> list[str]:
    return textwrap.wrap(t, n) or [""]


def _para(x: int, y: int, text: str, size: float = 14, fill: str = _INK, lh: int = 21, maxc: int = 80):
    lines = _wrap(text, maxc)
    out = [f'<text x="{x}" y="{y}" font-family="{_MONO}" font-size="{size}" fill="{fill}">']
    for i, ln in enumerate(lines):
        dy = "" if i == 0 else f' dy="{lh}"'
        out.append(f'<tspan x="{x}"{dy}>{_esc(ln)}</tspan>')
    out.append("</text>")
    return "".join(out), y + len(lines) * lh


def _sec_head(x: int, y: int, title: str):
    return (f'<text x="{x}" y="{y}" font-family="{_SANS}" font-weight="bold" font-size="13" '
            f'letter-spacing="2" fill="{_SEP}">{_esc(title)}</text>'
            f'<line x1="{x}" y1="{y + 8}" x2="{_RX}" y2="{y + 8}" stroke="{_SEP}" stroke-width="0.8"/>'), y + 28


def _section(x: int, y: int, title: str, body: str):
    h, y = _sec_head(x, y, title)
    if body:
        ps, y = _para(x, y + 2, body)
        h += ps
    return h, y + 16


def _sealed_block(x: int, y: int, title: str, rows: list[list[str]]):
    h, y = _sec_head(x, y, title)
    y += 4
    for row in rows:
        lab = row[0]
        w = max(120, min(320, 18 * len(lab)))
        h += f'<text x="{x}" y="{y}" font-family="{_MONO}" font-size="13" fill="{_SEP}">{_esc(lab)}</text>'
        h += f'<rect x="{x + 250}" y="{y - 13}" width="{w}" height="18" fill="{_BLK}"/>'
        h += f'<text x="{x + 250 + w + 8}" y="{y}" font-family="{_MONO}" font-size="10" fill="{_RED}">[SEALED]</text>'
        y += 24
    return h, y + 12


def _bg(paper_b64: str | None) -> str:
    if paper_b64:
        return (f'<image x="0" y="0" width="{_W}" height="{_H}" preserveAspectRatio="xMidYMid slice" '
                f'xlink:href="data:image/jpeg;base64,{paper_b64}"/>')
    out = [f'<rect x="0" y="0" width="{_W}" height="{_H}" fill="#dcd2b8"/>']
    for cx, cy, r in [(120, 200, 60), (660, 520, 70), (300, 980, 80), (600, 1080, 50)]:
        out.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{r}" ry="{int(r * 0.9)}" fill="none" '
                   f'stroke="#b08a4a" stroke-width="5" opacity="0.12"/>')
    return "".join(out)


def _open_svg(paper_b64: str | None, title: str, fileno: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{_W}" height="{_H}" viewBox="0 0 {_W} {_H}">' + _bg(paper_b64) +
            f'<rect x="{_LX}" y="40" width="150" height="34" fill="none" stroke="{_RED}" stroke-width="3"/>'
            f'<text x="{_LX + 75}" y="63" text-anchor="middle" font-family="{_HEAVY}" font-size="17" '
            f'fill="{_RED}" letter-spacing="1">TOP SECRET</text>'
            f'<text x="{_RX}" y="52" text-anchor="end" font-family="{_SANS}" font-weight="bold" font-size="15" '
            f'fill="{_INK}">RESEARCH &amp; ANALYSIS WING</text>'
            f'<text x="{_RX}" y="70" text-anchor="end" font-family="{_MONO}" font-size="12" fill="{_SEP}">'
            f'FILE {_esc(fileno)}  ·  {_esc(title)}</text>'
            f'<line x1="{_LX}" y1="86" x2="{_RX}" y2="86" stroke="{_SEP}" stroke-width="1"/>')


def _footer(page: int, total: int, codename: str) -> str:
    return (f'<line x1="{_LX}" y1="1170" x2="{_RX}" y2="1170" stroke="{_RED}" stroke-width="1.5"/>'
            f'<text x="{_LX}" y="1192" font-family="{_MONO}" font-size="11" fill="{_SEP}">'
            f'UNAUTHORISED DISCLOSURE — OFFICIAL SECRETS ACT 1923</text>'
            f'<text x="{_RX}" y="1192" text-anchor="end" font-family="{_MONO}" font-size="11" fill="{_SEP}">'
            f'{_esc(codename)}  ·  PAGE {page} OF {total}</text></svg>')


def _stamp(text: str) -> str:
    fs = min(56, int(440 / (0.62 * max(7, len(text)))))
    return (f'<g transform="rotate(-11 400 880)" opacity="0.8">'
            f'<rect x="150" y="828" width="500" height="104" fill="none" stroke="{_RED}" stroke-width="6"/>'
            f'<rect x="162" y="840" width="476" height="80" fill="none" stroke="{_RED}" stroke-width="2"/>'
            f'<text x="400" y="{868 + fs // 3}" text-anchor="middle" font-family="{_HEAVY}" font-size="{fs}" '
            f'fill="{_RED}" letter-spacing="2">{_esc(text)}</text></g>')


def _photo(port_b64: str | None) -> str:
    g = ['<g transform="rotate(-2 215 290)">',
         '<rect x="60" y="118" width="300" height="324" fill="#efeae1" stroke="#b6a684" stroke-width="1.5"/>']
    if port_b64:
        g.append('<clipPath id="pc"><rect x="68" y="126" width="284" height="308"/></clipPath>'
                 '<image x="68" y="126" width="284" height="308" preserveAspectRatio="xMidYMid slice" '
                 f'clip-path="url(#pc)" xlink:href="data:image/jpeg;base64,{port_b64}"/>')
    else:
        g.append('<rect x="68" y="126" width="284" height="308" fill="#23211c"/>'
                 '<text x="210" y="290" text-anchor="middle" font-family="' + _MONO + '" font-size="13" '
                 'fill="#6f685c">NO IMAGE ON FILE</text>')
    g.append('<rect x="198" y="110" width="24" height="40" rx="11" fill="none" stroke="#8d8d8d" stroke-width="3"/></g>')
    return "".join(g)


def _cover(paper: str | None, port: str | None, d: Dossier) -> str:
    s = [_open_svg(paper, "PERSONNEL DOSSIER", d.fileno), _photo(port)]
    y = 146
    for lab, val in (d.cover_rows or [["NAME", d.name], ["CODENAME", d.codename], ["STATUS", d.stamp]]):
        s.append(f'<text x="400" y="{y}" font-family="{_MONO}" font-size="14" letter-spacing="1" '
                 f'fill="{_SEP}">{_esc(lab)}</text>')
        if lab in d.redacted_cover:
            s.append(f'<rect x="566" y="{y - 14}" width="142" height="19" fill="{_BLK}"/>')
        else:
            s.append(f'<text x="558" y="{y}" font-family="{_MONO}" font-size="15" fill="{_INK}">{_esc(val)}</text>')
        y += 30
    s.append(f'<line x1="{_LX}" y1="478" x2="{_RX}" y2="478" stroke="{_SEP}" stroke-width="1"/>')
    blurb = ("CLASSIFICATION: TOP SECRET // EYES ONLY.  Provenance and status fields are sealed above this copy; "
             "see the assessment overleaf.")
    ps, _ = _para(_LX, 506, blurb)
    s.append(ps)
    s.append(_stamp(d.stamp))
    s.append(_footer(1, 3, d.codename))
    return "".join(s)


def _page2(paper: str | None, d: Dossier) -> str:
    s = [_open_svg(paper, "BACKGROUND & ASSESSMENT", d.fileno)]
    y = 124
    secs = d.sections or [["BACKGROUND", d.name + " — " + (d.appearance or "subject of record.")]]
    for t, b in secs[:2]:
        ps, y = _section(_LX, y, t, b)
        s.append(ps)
    if d.sealed:
        ps, y = _sealed_block(_LX, y, "SEALED — RESTRICTED ABOVE THIS COPY", d.sealed)
        s.append(ps)
    for t, b in secs[2:]:
        ps, y = _section(_LX, y, t, b)
        s.append(ps)
    if d.associates:
        ps, y = _sec_head(_LX, y, "KNOWN ASSOCIATES")
        s.append(ps)
        y += 4
        for ln in d.associates:
            s.append(f'<text x="{_LX}" y="{y}" font-family="{_MONO}" font-size="13" fill="{_INK}">{_esc(ln)}</text>')
            y += 22
    s.append(_footer(2, 3, d.codename))
    return "".join(s)


def _page3(paper: str | None, d: Dossier) -> str:
    s = [_open_svg(paper, "TRAINING & OPERATIONS", d.fileno)]
    y = 124
    ps, y = _section(_LX, y, "TRAINING", d.training or "On record.")
    s.append(ps)
    ps, y = _section(_LX, y, "CAPABILITIES", d.capabilities or "On record.")
    s.append(ps)
    ps, y = _sec_head(_LX, y, "OPERATIONAL RECORD — SELECTED")
    s.append(ps)
    y += 6
    for ln in (d.oplog or ["(no record on this copy)"]):
        s.append(f'<text x="{_LX}" y="{y}" font-family="{_MONO}" font-size="12.5" fill="{_INK}">{_esc(ln)}</text>')
        y += 19
    s.append(f'<text x="{_LX}" y="{y + 6}" font-family="{_MONO}" font-size="12.5" fill="{_SEP}">'
             f'{_esc(d.oplog_sealed_label)}</text>')
    s.append(f'<rect x="{_LX + 250}" y="{y - 7}" width="280" height="17" fill="{_BLK}"/>')
    s.append(f'<text x="{_LX + 250 + 288}" y="{y + 6}" font-family="{_MONO}" font-size="10" fill="{_RED}">[SEALED]</text>')
    y += 34
    s.append(f'<rect x="{_LX}" y="{y}" width="400" height="50" fill="none" stroke="{_RED}" stroke-width="2"/>')
    s.append(f'<text x="{_LX + 14}" y="{y + 22}" font-family="{_HEAVY}" font-size="14" fill="{_RED}">{_esc(d.threat)}</text>')
    s.append(f'<text x="{_LX + 14}" y="{y + 40}" font-family="{_MONO}" font-size="11.5" fill="{_SEP}">'
             f'{_esc(d.threat_detail)}</text>')
    y += 78
    ps, y = _section(_LX, y, "STANDING ORDERS", d.standing_orders or "Refer to case authority.")
    s.append(ps)
    s.append(f'<text x="{_LX}" y="{y + 16}" font-family="{_MONO}" font-size="12" fill="{_INK}">{_esc(d.authoriser)}</text>')
    s.append(_footer(3, 3, d.codename))
    return "".join(s)


def _compose(d: Dossier, paper: str | None, port: str | None, out_dir: Path) -> None:
    """Rasterize the three pages to a PDF and a side-by-side spread. No-op (leaves
    paths empty) if rsvg-convert is unavailable."""
    if not shutil.which("rsvg-convert"):
        return
    pages = [_cover(paper, port, d), _page2(paper, d), _page3(paper, d)]
    with tempfile.TemporaryDirectory() as td:
        svgs, pngs = [], []
        for i, p in enumerate(pages, 1):
            sp = Path(td) / f"p{i}.svg"
            sp.write_text(p, encoding="utf-8")
            svgs.append(str(sp))
            pp = Path(td) / f"p{i}.png"
            subprocess.run(["rsvg-convert", "-w", "900", str(sp), "-o", str(pp)], check=True)
            pngs.append(str(pp))
        pdf = out_dir / f"{d.character_id}.pdf"
        subprocess.run(["rsvg-convert", "-f", "pdf", *svgs, "-o", str(pdf)], check=True)
        d.pdf_path = str(pdf)
        try:
            from PIL import Image
            ims = [Image.open(p).convert("RGB").resize((900, 1372)) for p in pngs]
            gap, bg = 22, (26, 23, 18)
            canvas = Image.new("RGB", (900 * 3 + gap * 4, 1372 + gap * 2), bg)
            x = gap
            for im in ims:
                canvas.paste(im, (x, gap))
                x += 900 + gap
            spread = out_dir / f"{d.character_id}-spread.png"
            canvas.save(spread)
            d.spread_path = str(spread)
        except Exception:
            pass


def build_dossier_artifacts(state: BookState, out_dir: str | Path) -> list[str]:
    """Generate a portrait per subject and compose its PDF + spread. Returns the
    artifact paths written. Caches portraits and the paper so a re-run is cheap."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    portraits = out_dir / "portraits"
    portraits.mkdir(exist_ok=True)

    paper_b64: str | None = None
    paper_cache = out_dir / "_paper.jpg"
    if paper_cache.exists():
        paper_b64 = base64.b64encode(paper_cache.read_bytes()).decode()
    else:
        png = _gen_image(_PAPER_PROMPT, size="1024x1536")
        if png is not None:
            jpg = _to_jpeg_b64(png, 820)
            paper_cache.write_bytes(base64.b64decode(jpg))
            paper_b64 = jpg

    written: list[str] = []
    for d in state.authored.dossiers:
        port_b64: str | None = None
        cache = portraits / f"{d.character_id}.jpg"
        if cache.exists():
            port_b64 = base64.b64encode(cache.read_bytes()).decode()
        elif d.appearance:
            png = _gen_image(_PORTRAIT_TPL.format(look=d.appearance))
            if png is not None:
                port_b64 = _to_jpeg_b64(png, 520)
                cache.write_bytes(base64.b64decode(port_b64))
        _compose(d, paper_b64, port_b64, out_dir)
        if d.pdf_path:
            written.append(d.pdf_path)
        if d.spread_path:
            written.append(d.spread_path)
    return written
