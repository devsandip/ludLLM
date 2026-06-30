# Feature: story-graph studio (local, interactive)

Branch-local spec for `ludllm viz`, the interactive story-graph viewer. The
canonical data model and the no-leak contract live in
[../architecture.md](../architecture.md) and
[../../src/ludllm/state/schema.py](../../src/ludllm/state/schema.py); the graph
export contract is `state_to_graph` in
[../../src/ludllm/viz/export.py](../../src/ludllm/viz/export.py). This doc records
what the studio is and the decisions specific to it.

## What it is

A self-contained, local visualization of one novel's knowledge graph over
chapters. The reader of a generated book runs `ludllm viz runs/<proj>` and a
folder of static HTML opens in a browser. No server, no model calls, no internet.

The supersedes the single-`recording.json` replay demo for the local case: the
studio is per-novel, opens on the user's own book, and adds the secrets panel and
the detail/dossier surfaces.

## Architecture

- **Precompute in Python, render-only in JS.** All who-knows-what logic
  (`effective_beliefs`, reveals, story-time ordering) is resolved by the engine
  and frozen into an inlined data blob. The JS only restyles. This honors the
  same boundary as the replay demo: change the core semantics, regenerate, the
  page follows.
- **Self-contained viz folder, not a single file.** Portraits are small and are
  base64-inlined into `studio.html`. Dossier spreads/PDFs are large (~1.6 MB
  each) and are referenced by relative path, not inlined or duplicated.
- **One render target.** No Claude-artifact mode. The standalone HTML is the only
  renderer.

### Output layout

```
runs/<proj>/viz/
  studio.html              two-tab app (Story Graph + Dossiers); portraits inlined
  dossier_pages/<id>_pN.png  per-page images rasterized from the dossier PDF
  data.json                the studio data blob (debug aid; same data inlined in studio.html)
```

References `../04b_dossiers/<id>-spread.png` and `../04b_dossiers/<id>.pdf` for the
heavy dossier assets, and `../04b_dossiers/portraits/<id>.jpg` for portraits at
build time (inlined into studio.html).

## Data model (the inlined blob)

Built from `BookState` by the engine:

- `title`, `span` (chapter count), `eras` (id/label/year), `story_order`
  (chapters in story-time order), `chap[n]` = `{era, year, story_time, pov,
  present[], reader_reveals[]}`.
- `chars`: `{id, name, ini}` where `ini` is a disambiguated initials token
  (two-letter; on collision, first two of first + first two of last).
- `facts` (non-public only): `{id, label, tier, era, provenance, rr
  (reader_reveal_chapter), cr (character_reveal_chapter)}`.
- `trans[factId][charId]` = transition points `[[chapter, kind], ...]`, kind 1 =
  knows, 2 = falsely_believes; absence = does_not_know. Belief at chapter N = the
  last point with chapter <= N. Resolved by story time in the engine, so a
  flashback chapter correctly shows earlier knowledge.
- `events`: belief-change events `{ch, char, fact, type, src}` where type is
  `learns` (does_not_know -> knows) or `corrected` (falsely_believes -> knows);
  `deceived` is possible but absent in current books (false beliefs are authored,
  not mid-book events). `src` is the inferred transfer source: a character who was
  `present` in that chapter's scene and already knew the fact.
- `portraits[charId]` = base64 data URI (if a portrait exists).
- `dossier[charId]` = `dossier_<id>.html` filename (if a rendered dossier exists),
  else null.

## Color and shape grammar (locked)

- Belief: green `#1d9e75` knows/learns, red `#e24b4a` lie/deceived, gray
  `#b4b2a9` does-not-know, amber `#BA7517` corrected.
- Tier (secret nodes): purple ramp + size. hidden `#534AB7` (largest/darkest),
  delayed `#7F77DD`, never_explicit `#AFA9EC` (smallest, dashed). public excluded.
- Era (braid): low-chroma background wash; saturated chip only in the legend.
- Reader: blue `#378ADD`, first-class node (diamond).
- POV character: lane underline on the chapters they narrate.
- Knowledge dots (view A): one per held secret, green = knows, red = lie, size = tier.
- Transfer edges (view D): inferred (present + already-knew), dashed neutral arrows.

## Views (single page, view tabs)

All three share the chapter slider (sets N), the era wash, and the N-1/N/N+1
window highlight + playhead. Chapter is the x-axis.

- **A. Knowledge** (default): one lane per character + a Reader lane. Each lane
  carries a dot per secret the character holds at chapter N, anchored at the
  chapter they FIRST learned it (so authored knowledge clusters at ch 1 and
  acquired knowledge spreads across the timeline), colored by belief (green
  knows, red lie), sized by tier; the lane label shows the count. Dots vanish
  only on flashback chapters where the character does not yet hold the belief in
  story time (the braid, correct). The Reader lane shows reveal dots. POV
  underlines and era washes mark the braid. (This replaced an earlier
  event-marker swimlane, which was near-empty for books where knowledge is
  authored rather than learned mid-story.)
- **C. 3-chapter window**: full bipartite mesh for N-1, N, N+1 side by side.
  knows (green) / lie (red dashed) edges; characters left, secrets right (sized by
  tier). Middle panel ringed.
- **D. Propagation**: acquisition events as nodes on character lanes, with
  inferred transfer arrows. Sparse by nature.

## Layout and interaction

- **L1a fluid width**: the page fills the window with an 18px gutter each side, no
  max-width. Graph width follows the window (recomputed on resize).
- **L1b fixed-but-draggable height**: graph height is constant by default; the
  extra width goes to the chapter axis. A drag handle on the bottom edge of the
  graph lets the user make it taller (re-renders with re-spaced lanes / spread
  mesh). Same mechanic serves "drag view C taller."
- **Focus highlight**: selecting a secret dims everything not tied to it across
  the views (especially useful for the full-mesh C).

## Secrets panel (below the graph, two tabs)

- **Tab 1, "Reveals near chapter N":** two groups, revealed-only.
  - "Revealed until chapter N": secrets with reader_reveal <= N, most-recently-
    revealed first.
  - "Revealed in the next chapter": secrets with reader_reveal == N+1.
  - Nothing unrevealed or beyond N+1 ever shows. Each secret is its own swimlane on
    a chapter axis: an initials bubble sits at the chapter that character learned
    it; a diamond marks the reader reveal; a line marks N. A tier legend is shown.
- **Tab 2, "What each character knows at N":** per character, secrets known (green
  chips) and lies held (red chips, with the `false_value` on hover), with a count.

## Detail panel (right side; click to open)

Opened by clicking a secret or a character anywhere: in the graphs and in both
secrets tabs. Stacks below on a narrow window. Has a close control.

- **Secret selected:** full untruncated text, tier (+ meaning), provenance, era,
  reveal plan (reader/character reveal chapters + the gap), who knows / who holds a
  lie (with `false_value`) / who doesn't at N, and the per-character learn timeline
  (the Tab-1 swimlane reused). Selecting a secret also drives the focus highlight.
- **Character selected:** portrait + name + brief intro (the `role` line), what
  they know at N (secrets known + lies held), and a link to the full dossier that
  opens `dossier_<id>.html` in a new tab. No portrait/dossier -> initials avatar,
  no link.

## Dossiers

`studio.html` has two top-level tabs: **Story Graph** and **Dossiers**. They
share one page, so switching back to the graph preserves the chapter and any
selection. The Dossiers tab is hidden if no character has a rendered dossier.

- **Dossiers tab (the card grid):** 3-per-row cards, one per character that has a
  rendered dossier (others omitted). Each card shows the portrait, name, the
  `role` one-liner, birth year, and a backstory snippet, and opens that
  character's dossier in place.
- **Dossier view (inline):** the paginated viewer. At build time each page of the
  dossier PDF is rasterized to `dossier_pages/<id>_pN.png` (via pymupdf; falls
  back to splitting the spread image with Pillow if pymupdf is absent). It shows
  one image at a time with Back/Next buttons (and a "N / total" indicator), a
  "download PDF" link, and an "all dossiers" link back to the grid.
- The character detail panel's "Open dossier" switches to the Dossiers tab and
  opens that character inline.

Structured `Dossier` fields are empty in current books, so the viewer shows the
rendered page images, it does not re-render fields.

## CLI and dependencies

`ludllm viz runs/<proj> [--open]`: load the state, build the data, inline
portraits, rasterize dossier pages, write `viz/studio.html`,
`viz/dossier_pages/`, and `viz/data.json`. `--open` opens the browser. The PDF rasterization uses `pymupdf` and `pillow` from the `models`
extra (so the standard `uv sync --extra models` install covers it); without them,
viz still builds and degrades gracefully (spread-split, or no pagination).

## Out of scope (for now)

- Inline Claude-artifact rendering (dropped: too heavy for an artifact).
- Re-rendering dossiers from structured fields (the fields are empty; we paginate
  the rendered pages).

## Future

- The dossier stage should emit the individual page images alongside the combined
  PDF, so `ludllm viz` consumes them directly instead of rasterizing the PDF at
  build time (and pymupdf becomes optional rather than a `models` dependency).
- Deep-linking the selected character/chapter into the URL.
