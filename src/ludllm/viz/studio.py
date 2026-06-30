"""The local story-graph studio: an interactive, self-contained HTML view of one
novel's knowledge graph over chapters.

Precompute-in-Python, render-only-in-JS (same boundary as the replay demo): the
engine resolves all who-knows-what here and freezes it into an inlined data blob;
the page only restyles. See docs/features/story-graph-viz.md for the spec.

Public entry: `build_viz(project_dir)` writes `viz/studio.html` (a two-tab app:
Story Graph and Dossiers), `viz/dossier_pages/` (per-page images rasterized from
each dossier PDF), and `viz/data.json`. Portraits are inlined; the dossier page
images and PDFs are referenced by relative path.
"""

from __future__ import annotations

import base64
import json
import mimetypes
from pathlib import Path

from ludllm.state.schema import BookState


# ----- data extraction (the inlined blob) ----- #

def _initials(name: str) -> str:
    parts = [w for w in name.replace("(", " ").replace(")", " ").split() if w[:1].isalpha()]
    if not parts:
        return name[:2].upper()
    return (parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")).upper()


def _long_initials(name: str) -> str:
    parts = [w for w in name.split() if w[:1].isalpha()]
    if not parts:
        return name[:4]
    return (parts[0][:2] + (parts[-1][:2] if len(parts) > 1 else "")).title()


def _disambiguated_initials(characters) -> dict[str, str]:
    base = {c.id: _initials(c.name) for c in characters}
    buckets: dict[str, list[str]] = {}
    for cid, ini in base.items():
        buckets.setdefault(ini, []).append(cid)
    names = {c.id: c.name for c in characters}
    out: dict[str, str] = {}
    for ini, cids in buckets.items():
        if len(cids) == 1:
            out[cids[0]] = ini
        else:
            for cid in cids:
                out[cid] = _long_initials(names[cid])
    return out


def build_studio_data(state: BookState) -> dict:
    """Freeze the engine's knowledge graph into the render-only blob."""
    span = len(state.authored.chapter_outline) or max(
        (c.n for c in state.running.chapters), default=0
    )
    eras = [
        {"id": e.id, "label": e.label, "y0": e.year_start, "y1": e.year_end}
        for e in state.authored.world.eras
    ]
    era_ord = {e["id"]: i for i, e in enumerate(eras)}
    ini = _disambiguated_initials(state.authored.characters)
    chars = [{"id": c.id, "name": c.name, "ini": ini[c.id]} for c in state.authored.characters]

    beats = {b.n: b for b in state.authored.chapter_outline}
    chap = {}
    for n in range(1, span + 1):
        b = beats.get(n)
        chap[n] = {
            "era": state._resolve_era_id(n),
            "year": state._chapter_era_year(n),
            "st": (b.story_time if b else "") or "",
            "pov": (b.pov if b else None),
            "present": list(b.present) if b and b.present else [],
            "rr": list(b.reader_reveals) if b and b.reader_reveals else [],
        }

    def srank(n: int):
        y = chap[n]["year"]
        return (y if y is not None else 0, era_ord.get(chap[n]["era"], 0), n)

    story_order = sorted(range(1, span + 1), key=srank)

    facts = []
    for f in state.authored.facts:
        if f.tier.value == "public":
            continue
        facts.append({
            "id": f.id, "label": f.text, "tier": f.tier.value, "era": f.era_id,
            "prov": f.provenance.value,
            "rr": f.reveal.reader_reveal_chapter if f.reveal else None,
            "cr": f.reveal.character_reveal_chapter if f.reveal else None,
            "notes": getattr(f, "notes", "") or "",
        })
    fact_ids = {f["id"] for f in facts}

    kind = {"knows": 1, "falsely_believes": 2}
    trans = {f["id"]: {} for f in facts}
    false_values: dict[str, dict[str, str]] = {f["id"]: {} for f in facts}
    for c in state.authored.characters:
        arr = {fid: [0] * (span + 1) for fid in fact_ids}
        for n in range(1, span + 1):
            bel = state.effective_beliefs(c.id, n)
            for fid in fact_ids:
                b = bel.get(fid)
                arr[fid][n] = kind.get(b.kind.value, 0) if b else 0
                if b and b.kind.value == "falsely_believes" and b.false_value:
                    false_values[fid][c.id] = b.false_value
        for fid in fact_ids:
            pts, prev = [], None
            a = arr[fid]
            for n in range(1, span + 1):
                if a[n] != prev:
                    if not (prev is None and a[n] == 0):
                        pts.append([n, a[n]])
                    prev = a[n]
            if pts:
                trans[fid][c.id] = pts

    events = []
    for u in state.running.belief_updates:
        if u.fact_id not in fact_ids:
            continue
        prior = state.effective_beliefs(u.character_id, u.chapter).get(u.fact_id)
        pk = prior.kind.value if prior else "does_not_know"
        nk = u.kind.value
        if pk == nk:
            continue
        if nk == "knows":
            typ = "corrected" if pk == "falsely_believes" else "learns"
        elif nk == "falsely_believes":
            typ = "deceived"
        else:
            continue
        src = None
        present = chap[u.chapter]["present"]
        for c in state.authored.characters:
            if c.id == u.character_id or not present or c.id not in present:
                continue
            b = state.effective_beliefs(c.id, u.chapter).get(u.fact_id)
            if b and b.kind.value == "knows":
                src = c.id
                break
        events.append({"ch": u.chapter, "char": u.character_id, "fact": u.fact_id,
                       "type": typ, "src": src})

    return {
        "title": state.meta.title, "span": span, "eras": eras, "chars": chars,
        "facts": facts, "chap": {str(k): v for k, v in chap.items()},
        "story_order": story_order, "trans": trans, "false_values": false_values,
        "events": events, "roles": {c.id: c.role for c in state.authored.characters},
        "bios": {c.id: {"role": c.role, "born": c.born, "back": (c.backstory or "")[:200]}
                 for c in state.authored.characters},
        "portraits": {}, "dossier": {}, "dossier_pages": {},
    }


# ----- assets ----- #

def _data_uri(path: Path) -> str:
    mime = mimetypes.guess_type(str(path))[0] or "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def _collect_assets(project: Path, data: dict) -> None:
    """Inline portraits (small) and record which characters have a rendered
    dossier spread (referenced, not inlined)."""
    dossier_dir = project / "04b_dossiers"
    portraits_dir = dossier_dir / "portraits"
    for c in data["chars"]:
        cid = c["id"]
        p = portraits_dir / f"{cid}.jpg"
        if p.exists():
            data["portraits"][cid] = _data_uri(p)
        spread = dossier_dir / f"{cid}-spread.png"
        if spread.exists() or (dossier_dir / f"{cid}.pdf").exists():
            data["dossier"][cid] = f"dossier_{cid}.html"


def _pdf_to_pngs(pdf: Path, out_dir: Path, cid: str) -> list[str]:
    """Rasterize each PDF page to a PNG. Returns relative page paths, or [] if
    pymupdf is unavailable (the caller falls back to splitting the spread)."""
    try:
        import fitz
    except ImportError:
        return []
    if not pdf.exists():
        return []
    out_dir.mkdir(parents=True, exist_ok=True)
    rels: list[str] = []
    with fitz.open(pdf) as doc:
        for i, page in enumerate(doc, 1):
            page.get_pixmap(dpi=150).save(out_dir / f"{cid}_p{i}.png")
            rels.append(f"dossier_pages/{cid}_p{i}.png")
    return rels


def _split_spread(spread: Path, out_dir: Path, cid: str) -> list[str]:
    """Fallback when pymupdf is absent: split the 2-page spread image into a left
    and right page with Pillow."""
    if not spread.exists():
        return []
    try:
        from PIL import Image
    except ImportError:
        return []
    out_dir.mkdir(parents=True, exist_ok=True)
    im = Image.open(spread)
    w, h = im.size
    mid = w // 2
    im.crop((0, 0, mid, h)).save(out_dir / f"{cid}_p1.png")
    im.crop((mid, 0, w, h)).save(out_dir / f"{cid}_p2.png")
    return [f"dossier_pages/{cid}_p1.png", f"dossier_pages/{cid}_p2.png"]


def _rasterize_dossiers(project: Path, viz: Path, data: dict) -> None:
    dossier_dir = project / "04b_dossiers"
    pages_dir = viz / "dossier_pages"
    for c in data["chars"]:
        cid = c["id"]
        if cid not in data["dossier"]:
            continue
        pages = _pdf_to_pngs(dossier_dir / f"{cid}.pdf", pages_dir, cid)
        if not pages:
            pages = _split_spread(dossier_dir / f"{cid}-spread.png", pages_dir, cid)
        if pages:
            data["dossier_pages"][cid] = pages


# ----- rendering ----- #

def build_viz(project_dir: str | Path, *, open_browser: bool = False) -> Path:
    """Build the studio folder under `project_dir/viz/`. Returns studio.html path."""
    project = Path(project_dir)
    state = BookState.model_validate(json.loads((project / "book_state.json").read_text()))
    data = build_studio_data(state)
    _collect_assets(project, data)

    viz = project / "viz"
    viz.mkdir(parents=True, exist_ok=True)
    _rasterize_dossiers(project, viz, data)
    (viz / "data.json").write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")

    html = (_STUDIO_HTML.replace("__TITLE__", _esc(data["title"]))
            .replace("__DATA__", json.dumps(data, separators=(",", ":"))))
    studio = viz / "studio.html"
    studio.write_text(html, encoding="utf-8")

    if open_browser:
        import webbrowser
        webbrowser.open(studio.resolve().as_uri())
    return studio


def _esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


_STUDIO_HTML = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>__TITLE__ - story studio</title>
<style>
:root{--s0:#f7f6f3;--s1:#fff;--tp:#1c1b19;--ts:#6c6b66;--bd:rgba(0,0,0,0.14);--rad:8px;--acc:#378ADD;
--fs:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;}
@media(prefers-color-scheme:dark){:root{--s0:#191917;--s1:#232220;--tp:#ededea;--ts:#a3a29b;--bd:rgba(255,255,255,0.16);}}
*{box-sizing:border-box}
body{margin:0;background:var(--s0);color:var(--tp);font-family:var(--fs);line-height:1.5}
.page{margin:0;padding:20px 18px 56px}
h1{font-size:20px;font-weight:600;margin:0 0 2px}
.hdr{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap}
.toptabs{display:flex;gap:4px;margin:10px 0 16px;border-bottom:1px solid var(--bd)}
.ttab{border:none;background:none;border-bottom:2px solid transparent;border-radius:0;padding:8px 16px;font-size:14px;color:var(--ts);cursor:pointer}
.ttab.on{color:var(--tp);font-weight:600;border-bottom-color:var(--acc)}
.dgrid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}
@media(max-width:760px){.dgrid{grid-template-columns:1fr}}
.dcard{text-align:left;background:var(--s1);border:1px solid var(--bd);border-radius:12px;padding:14px 16px;cursor:pointer;font-family:inherit;color:inherit;transition:border-color .12s}
.dcard:hover{border-color:var(--acc)}
.dchd{display:flex;gap:12px;align-items:center;margin-bottom:8px}
.dchd img{width:56px;height:56px;border-radius:50%;object-fit:cover;border:1px solid var(--bd)}
.dav{width:56px;height:56px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:600;background:#378ADD22;color:#378ADD;border:1px solid #378ADD55}
.dnm{font-size:15px;font-weight:600;margin:0}
.drl{font-size:12px;color:var(--ts);margin:1px 0 0}
.dbk{font-size:13px;color:var(--ts);margin:0}
.dvbar{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:12px}
.dvbar img{width:48px;height:48px;border-radius:50%;object-fit:cover;border:1px solid var(--bd)}
.pageimg{max-width:100%;max-height:78vh;border:1px solid var(--bd);border-radius:8px;display:block;margin:0 auto;background:var(--s1)}
.dnav{display:flex;align-items:center;justify-content:center;gap:18px;margin-top:14px}
.dnav button{padding:7px 16px;font-size:14px}
a.dlink{color:var(--acc);text-decoration:none;font-size:13px}
.sub{font-size:13px;color:var(--ts);margin:0 0 16px}
.row{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.card{background:var(--s1);border:1px solid var(--bd);border-radius:12px;padding:14px 16px;margin-bottom:16px}
.main{display:flex;gap:16px;align-items:stretch}
.gcol{flex:1;min-width:0}
.panel{width:332px;flex:none;display:none}
.panel.open{display:block}
@media(max-width:780px){.main{flex-direction:column}.panel{width:auto}}
button{font-family:inherit;color:var(--tp);padding:5px 12px;border:1px solid var(--bd);border-radius:var(--rad);background:var(--s1);font-size:12px;cursor:pointer}
button:hover{border-color:var(--acc)}
button.on{border-color:var(--acc);font-weight:600}
input[type=range]{accent-color:var(--acc);height:20px;flex:1}
.chip{display:inline-flex;align-items:center;justify-content:center;font-size:11px;font-weight:600;border-radius:999px;padding:2px 7px;line-height:1.5;cursor:pointer}
.legend{display:flex;gap:14px;flex-wrap:wrap;font-size:12px;color:var(--ts);margin:8px 0 2px}
.muted{color:var(--ts);font-size:12px}
.seclane{border-bottom:1px solid var(--bd);padding:7px 0}
.seclane.click{cursor:pointer}
.seclane.click:hover{background:color-mix(in srgb,var(--acc) 7%,transparent)}
.grouphdr{font-size:12px;font-weight:600;color:var(--ts);margin:12px 0 4px;text-transform:uppercase;letter-spacing:.04em}
.handle{height:12px;cursor:ns-resize;display:flex;align-items:center;justify-content:center}
.handle::after{content:"";width:46px;height:3px;border-radius:2px;background:var(--bd)}
svg{display:block;width:100%;height:100%}
#gwrap{resize:vertical;overflow:hidden;min-height:240px;height:380px;border-bottom:1px dashed var(--bd)}
.pclose{float:right;border:none;background:none;font-size:16px;cursor:pointer;color:var(--ts);padding:0 4px}
.ptitle{font-size:15px;font-weight:600;margin:0 0 8px;padding-right:18px}
.kv{font-size:12px;color:var(--ts);margin:2px 0}
.kv b{color:var(--tp);font-weight:600}
.pimg{width:64px;height:64px;border-radius:50%;object-fit:cover;border:1px solid var(--bd)}
.avatar{width:64px;height:64px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:600;font-size:18px;background:#378ADD22;color:#378ADD;border:1px solid #378ADD55}
.sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
a.dlink{color:var(--acc);text-decoration:none;font-size:13px}
</style></head><body><div class="page">
<div class="hdr"><h1>__TITLE__</h1></div>
<div class="toptabs" id="toptabs"><button id="tabStory" class="ttab on">Story Graph</button><button id="tabDoss" class="ttab">Dossiers</button></div>
<div id="storyTab">
<p class="sub">Knowledge as a graph over chapters. Character belief resolves by story time; the reader by reading order. Drag the slider to move chapter N; click any secret or character for details.</p>
<h2 class="sr-only">Interactive story graph studio with three views, a secrets panel, and a detail panel.</h2>
<div class="main">
<div class="gcol">
<div class="card">
  <div class="row" style="justify-content:space-between">
    <div class="row"><span class="muted">View</span>
      <button id="vK" class="on">Knowledge</button>
      <button id="vC">3-chapter window</button>
      <button id="vD">Propagation</button></div>
  </div>
  <div id="readout" class="row" style="margin:10px 0 6px;font-size:13px"></div>
  <div id="gwrap"><svg id="g" role="img"></svg></div>
  <div class="handle" id="handle" title="drag to resize"></div>
  <div id="glegend" class="legend"></div>
  <div class="row" style="margin-top:8px">
    <span class="muted" id="chlab" style="min-width:74px">Chapter</span>
    <input type="range" id="slider" min="1" step="1"/>
    <span id="chval" style="font-size:13px;font-weight:600;min-width:26px;text-align:right"></span>
  </div>
  <div id="eralegend" class="legend"></div>
</div>
<div class="card">
  <div class="row"><span class="muted">Secrets</span>
    <button id="t1" class="on">Reveals near chapter N</button>
    <button id="t2">What each character knows</button></div>
  <div id="sec" style="margin-top:10px"></div>
</div>
</div>
<div class="card panel" id="panel"></div>
</div>
</div>
<div id="dossiersTab" style="display:none">
<div id="dossGrid" class="dgrid"></div>
<div id="dossView" style="display:none"></div>
</div>
<script>
const DATA = __DATA__;
const EC=["#BA7517","#378ADD","#534AB7","#1D9E75","#D4537E"];
const KNOW="#1d9e75",LIE="#e24b4a",UNK="#b4b2a9",CORR="#BA7517",RDR="#378ADD";
const TIERC={hidden:"#534AB7",delayed:"#7F77DD",never_explicit:"#AFA9EC"};
const TIERMEAN={hidden:"active secret, guarded from POVs who don't know it",delayed:"will surface on schedule",never_explicit:"hinted, never stated outright"};
const eidx={}; DATA.eras.forEach((e,i)=>eidx[e.id]=i);
const ecol=id=>EC[(eidx[id]??0)%EC.length];
const cName={},cIni={},cRole=DATA.roles||{}; DATA.chars.forEach(c=>{cName[c.id]=c.name;cIni[c.id]=c.ini;});
const fById={}; DATA.facts.forEach(f=>fById[f.id]=f);
const SPAN=DATA.span;
function beliefAt(fid,cid,n){const p=(DATA.trans[fid]||{})[cid];if(!p)return 0;let v=0;for(const q of p){if(q[0]<=n)v=q[1];else break;}return v;}
function firstKindCh(fid,cid,k){const p=(DATA.trans[fid]||{})[cid];if(!p)return 1;for(const q of p)if(q[1]===k)return q[0];return 1;}
function knowersAt(fid,n){return DATA.chars.map(c=>c.id).filter(id=>beliefAt(fid,id,n)===1);}
function liarsAt(fid,n){return DATA.chars.map(c=>c.id).filter(id=>beliefAt(fid,id,n)===2);}
function learnCh(fid,cid){const p=(DATA.trans[fid]||{})[cid];if(!p)return null;for(const q of p)if(q[1]===1)return q[0];return null;}
function readerKnows(f,n){return f.rr!=null&&n>=f.rr;}
function esc(s){return (s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;");}
function shortName(id){return (cName[id]||id).split(" (")[0];}
function wrap(t,n,m){const w=(t||"").split(" ");const L=[];let c="";for(const x of w){if((c+" "+x).trim().length>n){L.push(c.trim());c=x;if(L.length>=m)break;}else c+=" "+x;}if(L.length<m&&c.trim())L.push(c.trim());if(L.length===m&&c.trim())L[m-1]+="...";return L;}
let st={view:"K",n:1,sec:1,graphH:380,selKind:null,selId:null};

const slider=document.getElementById("slider"); slider.max=SPAN; slider.value=1;
function gW(){const w=document.getElementById("gwrap").clientWidth;return Math.max(360,w||900);}

function readout(){
  const c=DATA.chap[String(st.n)]||{};const ro=document.getElementById("readout");ro.innerHTML="";
  const col=ecol(c.era),lab=(DATA.eras[eidx[c.era]]||{}).label||"";
  const pill=document.createElement("span");
  pill.style.cssText="padding:3px 10px;border-radius:12px;font-weight:600;background:"+col+"22;color:"+col+";border:1px solid "+col+"66";
  pill.textContent=(c.year||"?")+"  "+lab.slice(0,32);ro.appendChild(pill);
  const m=document.createElement("span");m.className="muted";
  m.textContent=(c.st?c.st+"  ":"")+(c.pov?("POV "+(cIni[c.pov]||c.pov)):"");ro.appendChild(m);
}
function xCh(n,LM,W,RM){return LM+(W-LM-RM)*((n-1)/(SPAN-1||1));}
function dim(fid){return st.selKind==="secret"&&st.selId&&st.selId!==fid?0.22:null;}

function renderK(){
  const W=gW(),LM=128,RM=16,TOP=16,H=st.graphH,lanes=DATA.chars.length+1,laneH=Math.max(20,(H-TOP-8)/lanes);
  const g=document.getElementById("g");g.setAttribute("viewBox","0 0 "+W+" "+H);
  const step=(W-LM-RM)/(SPAN-1||1);
  const yR=TOP+laneH/2,yC=i=>TOP+laneH*(i+1)+laneH/2;let p=[];
  for(let n=1;n<=SPAN;n++){const c=DATA.chap[String(n)]||{};const cx=xCh(n,LM,W,RM);
    p.push('<rect x="'+(cx-step/2).toFixed(1)+'" y="'+TOP+'" width="'+step.toFixed(1)+'" height="'+(H-TOP-4)+'" fill="'+ecol(c.era)+'" opacity="0.08"/>');}
  for(const n of [st.n-1,st.n,st.n+1])if(n>=1&&n<=SPAN){const cx=xCh(n,LM,W,RM);
    p.push('<rect x="'+(cx-step/2).toFixed(1)+'" y="'+TOP+'" width="'+step.toFixed(1)+'" height="'+(H-TOP-4)+'" fill="'+RDR+'" opacity="0.10"/>');}
  const px=xCh(st.n,LM,W,RM);
  p.push('<line x1="'+px.toFixed(1)+'" y1="'+TOP+'" x2="'+px.toFixed(1)+'" y2="'+(H-4)+'" stroke="'+RDR+'" stroke-width="1.5"/>');
  function dots(items,yc){const groups={};items.forEach(it=>{(groups[it.ch]=groups[it.ch]||[]).push(it);});
    for(const ch in groups){const arr=groups[ch],cx=xCh(+ch,LM,W,RM),band=Math.max(6,laneH-8),sp=Math.min(8,band/(arr.length+1));
      arr.forEach((it,j)=>{const dy=(j-(arr.length-1)/2)*sp,o=dim(it.fid);
        p.push('<circle data-fact="'+it.fid+'" cx="'+cx.toFixed(1)+'" cy="'+(yc+dy).toFixed(1)+'" r="'+it.r+'" fill="'+it.col+'" stroke="'+it.stroke+'" stroke-width="1" style="cursor:pointer" opacity="'+(o!=null?o:0.92)+'"><title>'+esc(it.title)+'</title></circle>');});}}
  p.push('<line x1="'+LM+'" y1="'+yR.toFixed(1)+'" x2="'+(W-RM)+'" y2="'+yR.toFixed(1)+'" stroke="var(--bd)" stroke-width="1"/>');
  const rdr=[];for(const f of DATA.facts){if(f.rr!=null&&f.rr<=st.n)rdr.push({ch:f.rr,fid:f.id,col:RDR,stroke:"none",r:3.4,title:f.label.slice(0,70)});}
  p.push('<text x="8" y="'+(yR+4).toFixed(1)+'" font-size="12" font-weight="600" fill="'+RDR+'">Reader ('+rdr.length+')</text>');
  dots(rdr,yR);
  DATA.chars.forEach((c,i)=>{const y=yC(i);
    p.push('<line x1="'+LM+'" y1="'+y.toFixed(1)+'" x2="'+(W-RM)+'" y2="'+y.toFixed(1)+'" stroke="var(--bd)" stroke-width="1" opacity="0.7"/>');
    for(let n=1;n<=SPAN;n++){const ch=DATA.chap[String(n)];if(ch&&ch.pov===c.id){const cx=xCh(n,LM,W,RM);
      p.push('<line x1="'+(cx-step/2+1).toFixed(1)+'" y1="'+(y+laneH/2-4).toFixed(1)+'" x2="'+(cx+step/2-1).toFixed(1)+'" y2="'+(y+laneH/2-4).toFixed(1)+'" stroke="var(--ts)" stroke-width="2" opacity="0.4"/>');}}
    const items=[];for(const f of DATA.facts){const k=beliefAt(f.id,c.id,st.n);if(k){const r=({hidden:4.5,delayed:3.6,never_explicit:3})[f.tier]||3.6;
      items.push({ch:firstKindCh(f.id,c.id,k),fid:f.id,col:k===1?KNOW:LIE,stroke:k===2?LIE:"none",r:r,title:f.label.slice(0,70)});}}
    p.push('<text data-char="'+c.id+'" x="8" y="'+(y+4).toFixed(1)+'" font-size="12" fill="var(--tp)" style="cursor:pointer"><tspan font-weight="600">'+esc(c.ini)+'</tspan> '+esc(shortName(c.id).slice(0,11))+' ('+items.length+')</text>');
    dots(items,y);});
  g.innerHTML=p.join("");
  setLegend([["knows (dot = when entered)",KNOW],["holds a lie",LIE],["reader knows",RDR],["size = tier","var(--ts)"]]);
}

function renderC(){
  const W=gW(),H=st.graphH,pad=14;const cols=[st.n-1,st.n,st.n+1].filter(n=>n>=1&&n<=SPAN);
  const g=document.getElementById("g");g.setAttribute("viewBox","0 0 "+W+" "+H);
  const active=DATA.facts.filter(f=>cols.some(n=>knowersAt(f.id,n).length||liarsAt(f.id,n).length));
  const LM=96,bandsLeft=LM+12,bandW=(W-pad-bandsLeft)/Math.max(1,cols.length);
  const top=40,bh=H-58;
  const yc=i=>top+bh*(i/Math.max(1,DATA.chars.length-1));
  const yf=i=>top+bh*(i/Math.max(1,active.length-1));
  const fxOf=ci=>bandsLeft+ci*bandW+bandW-26;let p=[];
  cols.forEach((n,ci)=>{const c=DATA.chap[String(n)]||{},x0=bandsLeft+ci*bandW;
    p.push('<rect x="'+(x0+2).toFixed(1)+'" y="6" width="'+(bandW-4).toFixed(1)+'" height="'+(H-12)+'" rx="10" fill="'+ecol(c.era)+'" opacity="0.07" stroke="'+(n===st.n?RDR:"var(--bd)")+'" stroke-width="'+(n===st.n?2:1)+'"/>');
    p.push('<text x="'+(x0+bandW/2).toFixed(1)+'" y="22" font-size="12" font-weight="600" text-anchor="middle" fill="var(--tp)">ch '+n+(c.year?(" · "+c.year):"")+'</text>');});
  cols.forEach((n,ci)=>{const fx=fxOf(ci);active.forEach((f,fi)=>{const o=dim(f.id);DATA.chars.forEach((c2,i)=>{const k=beliefAt(f.id,c2.id,n);if(k===0)return;
    p.push('<line x1="'+LM+'" y1="'+yc(i).toFixed(1)+'" x2="'+fx.toFixed(1)+'" y2="'+yf(fi).toFixed(1)+'" stroke="'+(k===1?KNOW:LIE)+'" stroke-width="1.1" stroke-dasharray="'+(k===2?"3 2":"")+'" opacity="'+(o!=null?o:0.6)+'"/>');});});});
  cols.forEach((n,ci)=>{const fx=fxOf(ci);active.forEach((f,fi)=>{const o=dim(f.id),sz=({hidden:4,delayed:3.4,never_explicit:2.8})[f.tier]||3.4;
    p.push('<rect data-fact="'+f.id+'" x="'+(fx-sz).toFixed(1)+'" y="'+(yf(fi)-sz).toFixed(1)+'" width="'+(2*sz).toFixed(1)+'" height="'+(2*sz).toFixed(1)+'" fill="'+(TIERC[f.tier]||"#7F77DD")+'" stroke="'+(readerKnows(f,n)?RDR:"none")+'" stroke-width="1.5" style="cursor:pointer" opacity="'+(o!=null?o:1)+'"/>');});});
  DATA.chars.forEach((c2,i)=>{const y=yc(i);
    p.push('<circle data-char="'+c2.id+'" cx="'+LM+'" cy="'+y.toFixed(1)+'" r="4.5" fill="var(--tp)" style="cursor:pointer"/>');
    p.push('<text data-char="'+c2.id+'" x="'+(LM-9)+'" y="'+(y+3).toFixed(1)+'" font-size="10" text-anchor="end" style="cursor:pointer"><tspan font-weight="600" fill="var(--tp)">'+esc(c2.ini)+'</tspan> <tspan fill="var(--ts)">'+esc(shortName(c2.id).slice(0,8))+'</tspan></text>');});
  g.innerHTML=p.join("");
  setLegend([["knows",KNOW],["believes a lie",LIE],["secret (blue edge = reader knows)",RDR]]);
}

function renderD(){
  const W=gW(),LM=128,RM=16,TOP=16,H=st.graphH,laneH=Math.max(20,(H-TOP-8)/DATA.chars.length);
  const g=document.getElementById("g");g.setAttribute("viewBox","0 0 "+W+" "+H);
  const yC=i=>TOP+laneH*i+laneH/2;const idx={};DATA.chars.forEach((c,i)=>idx[c.id]=i);let p=[];
  const px=xCh(st.n,LM,W,RM);
  p.push('<rect x="'+LM+'" y="'+TOP+'" width="'+(px-LM).toFixed(1)+'" height="'+(H-TOP-4)+'" fill="'+RDR+'" opacity="0.05"/>');
  p.push('<line x1="'+px.toFixed(1)+'" y1="'+TOP+'" x2="'+px.toFixed(1)+'" y2="'+(H-4)+'" stroke="'+RDR+'" stroke-width="1.5"/>');
  DATA.chars.forEach((c,i)=>{const y=yC(i);
    p.push('<line x1="'+LM+'" y1="'+y.toFixed(1)+'" x2="'+(W-RM)+'" y2="'+y.toFixed(1)+'" stroke="var(--bd)" stroke-width="1" opacity="0.5"/>');
    p.push('<text data-char="'+c.id+'" x="8" y="'+(y+4).toFixed(1)+'" font-size="12" fill="var(--tp)" style="cursor:pointer"><tspan font-weight="600">'+esc(c.ini)+'</tspan> '+esc(shortName(c.id).slice(0,13))+'</text>');});
  for(const e of DATA.events){if(idx[e.char]==null||!e.src||idx[e.src]==null)continue;const cx=xCh(e.ch,LM,W,RM),o=dim(e.fact),op=o!=null?o:(e.ch<=st.n?0.85:0.2);
    p.push('<line x1="'+cx.toFixed(1)+'" y1="'+yC(idx[e.src]).toFixed(1)+'" x2="'+cx.toFixed(1)+'" y2="'+yC(idx[e.char]).toFixed(1)+'" stroke="var(--ts)" stroke-width="1.4" stroke-dasharray="3 3" opacity="'+op+'" marker-end="url(#ar)"/>');}
  for(const e of DATA.events){if(idx[e.char]==null)continue;const cx=xCh(e.ch,LM,W,RM),y=yC(idx[e.char]),o=dim(e.fact),op=o!=null?o:(e.ch<=st.n?1:0.25),col=e.type==="corrected"?CORR:KNOW,f=fById[e.fact];
    p.push('<g data-fact="'+e.fact+'" style="cursor:pointer" opacity="'+op+'"><circle cx="'+cx.toFixed(1)+'" cy="'+y.toFixed(1)+'" r="5" fill="'+col+'"/><text x="'+cx.toFixed(1)+'" y="'+(y-8).toFixed(1)+'" font-size="9" text-anchor="middle" fill="var(--ts)">'+esc((f?f.label:e.fact).slice(0,16))+'</text></g>');}
  g.innerHTML='<defs><marker id="ar" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0 L10 5 L0 10 z" fill="var(--ts)"/></marker></defs>'+p.join("");
  setLegend([["acquisition event",KNOW],["corrected",CORR],["inferred source (present + knew)","var(--ts)"]]);
}

function setLegend(items){document.getElementById("glegend").innerHTML=items.map(([t,c])=>'<span><span style="display:inline-block;width:11px;height:11px;border-radius:2px;background:'+c+';vertical-align:middle"></span> '+t+'</span>').join("");}
function renderGraph(){readout();document.getElementById("chval").textContent=st.n;slider.value=st.n;
  if(st.view==="C")renderC();else if(st.view==="D")renderD();else renderK();}

function secretLaneSVG(f,N){
  const W=560,LM=8,RM=10;const x=ch=>LM+(W-LM-RM)*((ch-1)/(SPAN-1||1));
  let p=['<line x1="'+LM+'" y1="14" x2="'+(W-RM)+'" y2="14" stroke="var(--bd)" stroke-width="1"/>'];
  const pn=x(N);p.push('<line x1="'+pn.toFixed(1)+'" y1="2" x2="'+pn.toFixed(1)+'" y2="26" stroke="'+RDR+'" stroke-width="1" opacity="0.5"/>');
  if(f.rr!=null&&f.rr<=SPAN){const xr=x(f.rr);p.push('<path d="M'+xr.toFixed(1)+' 8 l4 6 l-4 6 l-4 -6 z" fill="'+(readerKnows(f,N)?RDR:"none")+'" stroke="'+RDR+'" stroke-width="1.3"/>');}
  knowersAt(f.id,N).forEach(cid=>{const lc=learnCh(f.id,cid)||1,cx=x(lc);
    p.push('<circle cx="'+cx.toFixed(1)+'" cy="14" r="8" fill="'+KNOW+'22" stroke="'+KNOW+'" stroke-width="1"/>');
    p.push('<text x="'+cx.toFixed(1)+'" y="17.5" font-size="8.5" font-weight="600" text-anchor="middle" fill="'+KNOW+'">'+esc(cIni[cid])+'</text>');});
  return '<svg viewBox="0 0 '+W+' 28" width="100%" style="max-width:560px;margin-top:3px"><g>'+p.join("")+'</g></svg>';
}
function tierChip(tier){const c=TIERC[tier]||"#7F77DD";return '<span class="chip" style="background:'+c+'22;color:'+c+';border:1px solid '+c+'66" title="'+(TIERMEAN[tier]||"")+'">'+tier+'</span>';}

function renderSec1(){
  const N=st.n,sec=document.getElementById("sec");
  const until=DATA.facts.filter(f=>f.rr!=null&&f.rr<=N).sort((a,b)=>(b.rr-a.rr));
  const next=DATA.facts.filter(f=>f.rr!=null&&f.rr===N+1).sort((a,b)=>(a.label<b.label?-1:1));
  function row(f){return '<div class="seclane click" onclick="selectSecret(\''+f.id+'\')"><div class="row" style="gap:8px">'+tierChip(f.tier)+'<span style="font-size:13px;flex:1;min-width:200px">'+esc(f.label.slice(0,92))+'</span></div>'+secretLaneSVG(f,N)+'</div>';}
  let h='<div class="legend"><span>'+tierChip("hidden")+' active secret</span><span>'+tierChip("delayed")+' surfaces on schedule</span><span>'+tierChip("never_explicit")+' implied, never stated</span></div>';
  h+='<div class="muted" style="margin:4px 0 6px">Each lane is one secret on a chapter axis. An initials bubble sits at the chapter that character learned it; the diamond is the reader reveal; the blue line is chapter N.</div>';
  h+='<div class="grouphdr">Revealed until chapter '+N+'</div>'+(until.length?until.map(row).join(""):'<div class="muted">Nothing revealed yet.</div>');
  h+='<div class="grouphdr">Revealed in the next chapter</div>'+(next.length?next.map(row).join(""):'<div class="muted">No reveal in chapter '+(N+1)+'.</div>');
  sec.innerHTML=h;
}
function renderSec2(){
  const N=st.n,sec=document.getElementById("sec");
  let h='<div class="muted" style="margin-bottom:8px">Secrets each character knows as of chapter '+N+' (by story time). Red = holds a false belief. Click a name or secret for details.</div>';
  h+=DATA.chars.map(c=>{
    const known=DATA.facts.filter(f=>beliefAt(f.id,c.id,N)===1),lied=DATA.facts.filter(f=>beliefAt(f.id,c.id,N)===2);
    const chips=known.map(f=>'<span class="chip" onclick="selectSecret(\''+f.id+'\')" style="background:'+KNOW+'18;color:'+KNOW+';border:1px solid '+KNOW+'55" title="'+esc(f.label)+'">'+esc(f.label.slice(0,30))+'</span>').join(" ")
      +" "+lied.map(f=>'<span class="chip" onclick="selectSecret(\''+f.id+'\')" style="background:'+LIE+'18;color:'+LIE+';border:1px solid '+LIE+'55" title="'+esc(f.label)+'">'+esc(f.label.slice(0,26))+'</span>').join(" ");
    return '<div class="seclane"><div class="row" style="gap:8px;align-items:baseline"><span class="chip" onclick="selectChar(\''+c.id+'\')" style="background:#378ADD22;color:#378ADD;border:1px solid #378ADD66;min-width:30px">'+esc(c.ini)+'</span><span style="font-size:13px;font-weight:600;min-width:120px;cursor:pointer" onclick="selectChar(\''+c.id+'\')">'+esc(shortName(c.id))+'</span><span class="muted">'+known.length+' known</span></div><div style="margin-top:5px">'+(chips.trim()||'<span class="muted">nothing yet</span>')+'</div></div>';
  }).join("");
  sec.innerHTML=h;
}
function renderSec(){st.sec===1?renderSec1():renderSec2();}

function panelEl(){return document.getElementById("panel");}
function closePanel(){st.selKind=null;st.selId=null;panelEl().classList.remove("open");renderGraph();}
function selectSecret(fid){st.selKind="secret";st.selId=fid;renderPanel();renderGraph();}
function selectChar(cid){st.selKind="char";st.selId=cid;renderPanel();}
function renderPanel(){
  const pe=panelEl(),N=st.n;pe.classList.add("open");
  if(st.selKind==="secret"){const f=fById[st.selId];if(!f){closePanel();return;}
    const know=knowersAt(f.id,N),lie=liarsAt(f.id,N);
    const gap=(f.rr!=null&&f.cr!=null)?(f.cr-f.rr):null;
    let h='<button class="pclose" onclick="closePanel()">&times;</button>';
    h+='<div class="ptitle">'+tierChip(f.tier)+'</div>';
    h+='<p style="font-size:13px;margin:0 0 10px">'+esc(f.label)+'</p>';
    h+='<div class="kv"><b>Tier:</b> '+f.tier+' — '+(TIERMEAN[f.tier]||"")+'</div>';
    h+='<div class="kv"><b>Provenance:</b> '+esc(f.prov||"invented")+'</div>';
    if(f.era)h+='<div class="kv"><b>Era:</b> '+esc((DATA.eras[eidx[f.era]]||{}).label||f.era)+'</div>';
    h+='<div class="kv"><b>Reader reveal:</b> '+(f.rr!=null?("ch "+f.rr):"—")+'   <b>Character reveal:</b> '+(f.cr!=null?("ch "+f.cr):"—")+(gap!=null?('   <b>gap:</b> '+gap+' ch'):"")+'</div>';
    h+='<div class="kv" style="margin-top:8px"><b>Learn timeline</b></div>'+secretLaneSVG(f,N);
    h+='<div class="kv" style="margin-top:8px"><b>Knows now ('+know.length+'):</b></div><div>'+(know.length?know.map(id=>'<span class="chip" onclick="selectChar(\''+id+'\')" style="background:'+KNOW+'18;color:'+KNOW+';border:1px solid '+KNOW+'55">'+esc(cIni[id])+'</span>').join(" "):'<span class="muted">none</span>')+'</div>';
    if(lie.length){h+='<div class="kv" style="margin-top:8px"><b>Believes a lie:</b></div><div>'+lie.map(id=>{const fv=(DATA.false_values[f.id]||{})[id]||"";return '<span class="chip" onclick="selectChar(\''+id+'\')" style="background:'+LIE+'18;color:'+LIE+';border:1px solid '+LIE+'55" title="'+esc(fv)+'">'+esc(cIni[id])+'</span>';}).join(" ")+'</div>';}
    if(f.notes)h+='<div class="kv" style="margin-top:8px"><b>Notes:</b> '+esc(f.notes)+'</div>';
    pe.innerHTML=h;
  }else if(st.selKind==="char"){const cid=st.selId,name=cName[cid]||cid;
    const known=DATA.facts.filter(f=>beliefAt(f.id,cid,N)===1),lied=DATA.facts.filter(f=>beliefAt(f.id,cid,N)===2);
    const port=(DATA.portraits||{})[cid],hasDoss=!!(DATA.dossier_pages||{})[cid];
    let h='<button class="pclose" onclick="closePanel()">&times;</button>';
    h+='<div class="row" style="gap:12px;align-items:flex-start">'+(port?('<img class="pimg" src="'+port+'" alt=""/>'):('<div class="avatar">'+esc(cIni[cid])+'</div>'))+'<div><div class="ptitle" style="margin:0">'+esc(shortName(cid))+'</div><div class="muted">'+esc(cRole[cid]||"")+'</div>'+(hasDoss?('<a class="dlink" style="cursor:pointer" onclick="openDossierFromPanel(\''+cid+'\')">Open dossier &rarr;</a>'):'<span class="muted">no dossier</span>')+'</div></div>';
    h+='<div class="kv" style="margin-top:10px"><b>Knows at ch '+N+' ('+known.length+'):</b></div><div>'+(known.length?known.map(f=>'<span class="chip" onclick="selectSecret(\''+f.id+'\')" style="background:'+KNOW+'18;color:'+KNOW+';border:1px solid '+KNOW+'55" title="'+esc(f.label)+'">'+esc(f.label.slice(0,28))+'</span>').join(" "):'<span class="muted">nothing yet</span>')+'</div>';
    if(lied.length)h+='<div class="kv" style="margin-top:8px"><b>Holds a lie about:</b></div><div>'+lied.map(f=>'<span class="chip" onclick="selectSecret(\''+f.id+'\')" style="background:'+LIE+'18;color:'+LIE+';border:1px solid '+LIE+'55" title="'+esc(f.label)+'">'+esc(f.label.slice(0,26))+'</span>').join(" ")+'</div>';
    pe.innerHTML=h;
  }
}

function setView(v){st.view=v;["K","C","D"].forEach(k=>document.getElementById("v"+k).classList.toggle("on",k===v));renderGraph();}
function setTab(t){st.sec=t;document.getElementById("t1").classList.toggle("on",t===1);document.getElementById("t2").classList.toggle("on",t===2);renderSec();}
document.getElementById("vK").onclick=()=>setView("K");
document.getElementById("vC").onclick=()=>setView("C");
document.getElementById("vD").onclick=()=>setView("D");
document.getElementById("t1").onclick=()=>setTab(1);
document.getElementById("t2").onclick=()=>setTab(2);
slider.oninput=e=>{st.n=+e.target.value;renderGraph();renderSec();if(st.selKind)renderPanel();};
document.getElementById("g").addEventListener("click",e=>{const t=e.target.closest("[data-fact],[data-char]");if(!t){if(st.selKind)closePanel();return;}if(t.dataset.fact)selectSecret(t.dataset.fact);else if(t.dataset.char)selectChar(t.dataset.char);});
const gwrap=document.getElementById("gwrap"),handle=document.getElementById("handle");
handle.addEventListener("mousedown",e=>{e.preventDefault();const y0=e.clientY,h0=gwrap.clientHeight;
  function mv(ev){gwrap.style.height=Math.max(240,Math.min(1600,h0+(ev.clientY-y0)))+"px";}
  function up(){document.removeEventListener("mousemove",mv);document.removeEventListener("mouseup",up);}
  document.addEventListener("mousemove",mv);document.addEventListener("mouseup",up);});
const _ro=new ResizeObserver(()=>{st.graphH=Math.max(200,gwrap.clientHeight);renderGraph();});
_ro.observe(gwrap);
document.getElementById("eralegend").innerHTML=DATA.eras.map((e,i)=>'<span><span style="display:inline-block;width:11px;height:11px;border-radius:2px;background:'+EC[i]+';vertical-align:middle"></span> '+e.y0+(e.y1!==e.y0?("–"+e.y1):"")+" "+esc((e.label||"").slice(0,28))+'</span>').join("");
function dossChars(){return DATA.chars.filter(c=>(DATA.dossier_pages||{})[c.id]);}
function setTopTab(t){document.getElementById("storyTab").style.display=t==="story"?"":"none";document.getElementById("dossiersTab").style.display=t==="doss"?"":"none";document.getElementById("tabStory").classList.toggle("on",t==="story");document.getElementById("tabDoss").classList.toggle("on",t==="doss");if(t==="doss")showDossGrid();}
function showDossGrid(){document.getElementById("dossView").style.display="none";const g=document.getElementById("dossGrid");g.style.display="";g.innerHTML=dossChars().map(c=>{const bio=(DATA.bios||{})[c.id]||{},port=(DATA.portraits||{})[c.id],born=bio.born?(" &middot; b. "+bio.born):"",thumb=port?('<img src="'+port+'" alt=""/>'):('<div class="dav">'+esc(c.ini)+'</div>');return '<button class="dcard" onclick="openDossier(\''+c.id+'\')"><div class="dchd">'+thumb+'<div><p class="dnm">'+esc(shortName(c.id))+'</p><p class="drl">'+esc(bio.role||"")+born+'</p></div></div><p class="dbk">'+esc(bio.back||"")+'</p></button>';}).join("");}
let dossSt={cid:null,i:0};
function openDossier(cid){const pages=(DATA.dossier_pages||{})[cid];if(!pages)return;dossSt={cid:cid,i:0};document.getElementById("dossGrid").style.display="none";const v=document.getElementById("dossView");v.style.display="";const port=(DATA.portraits||{})[cid];v.innerHTML='<div class="dvbar">'+(port?('<img src="'+port+'" alt=""/>'):'')+'<div><div style="font-weight:600">'+esc(shortName(cid))+'</div><div class="muted">'+esc(cRole[cid]||"")+'</div></div><span style="flex:1"></span><button class="ttab" onclick="showDossGrid()">&larr; All dossiers</button><a class="dlink" href="../04b_dossiers/'+cid+'.pdf" target="_blank" rel="noopener">Download PDF &#8599;</a></div><img id="dpg" class="pageimg" alt="dossier page"/><div class="dnav"><button id="dprev">&larr; Back</button><span id="dind" class="muted" style="min-width:54px;text-align:center"></span><button id="dnext">Next &rarr;</button></div>';document.getElementById("dprev").onclick=function(){if(dossSt.i>0){dossSt.i--;showDossPage();}};document.getElementById("dnext").onclick=function(){const p=(DATA.dossier_pages||{})[dossSt.cid];if(dossSt.i<p.length-1){dossSt.i++;showDossPage();}};showDossPage();window.scrollTo(0,0);}
function showDossPage(){const pages=(DATA.dossier_pages||{})[dossSt.cid];document.getElementById("dpg").src=pages[dossSt.i];document.getElementById("dind").textContent=(dossSt.i+1)+" / "+pages.length;document.getElementById("dprev").disabled=dossSt.i===0;document.getElementById("dnext").disabled=dossSt.i===pages.length-1;}
function openDossierFromPanel(cid){setTopTab("doss");openDossier(cid);}
document.getElementById("tabStory").onclick=function(){setTopTab("story");};
document.getElementById("tabDoss").onclick=function(){setTopTab("doss");};
if(!dossChars().length)document.getElementById("toptabs").style.display="none";
renderGraph();renderSec();
</script></div></body></html>
"""
