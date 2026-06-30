# LudLLM

An agentic pipeline that writes a full-length novel end to end. The experiment:
how far a generation-plus-judgment loop can be pushed over 80k+ words while
staying coherent and not reading like a machine wrote it.

The thesis: word production is not the bottleneck. Coherence and taste are. The
architecture exists to protect those two.

## How it works

A novel is too long for any context window, so all state lives in one validated
JSON object and the system works one chapter at a time. Setup runs in gated
stages (normalize, world + secrets, cast + beliefs, structure, outline); then the
chapter loop drafts on a scoped, no-leak context, extracts what it established
back into state, critiques with a different model family, and revises. A secret is
physically denied to the drafter until its scheduled reveal, so the
reader-vs-character information asymmetry is enforced at generation time, not
patched afterward. Time is a first-class axis: each era carries a capability
baseline, and knowledge accrues in story time so a braided timeline stays honest.

See [docs/architecture.md](docs/architecture.md) for the full design and
[docs/novel-pipeline-primer.md](docs/novel-pipeline-primer.md) for the idea.

## Try it offline (no keys, no tokens)

```bash
uv sync                          # or: pip install -e .
uv run ludllm demo ./out         # runs the bundled example end to end on mock models
uv run ludllm graph ./out/book_state.json -c 9   # export the story graph at chapter 9
uv run ludllm show ./out/book_state.json
```

## The story-graph studio

`ludllm viz runs/<project>` builds a self-contained, interactive view of one
book's knowledge graph into `runs/<project>/viz/studio.html`. Open it in any
browser, no server: a Story Graph tab with chapter-axis views of who knows which
secret and since when, a revealed-only secrets panel, and click-to-open detail
panels for any secret or character; and a Dossiers tab with a card grid and a
paginated dossier viewer. All epistemic logic stays in the engine core; the page
only renders precomputed data. See
[docs/features/story-graph-viz.md](docs/features/story-graph-viz.md).

Two finished sample novels ship under `runs/alpha` and `runs/alpha-v2`, so you can
open the studio on real output right away:

```bash
uv sync --extra models         # pymupdf (dossier pages) rides along with this extra
uv run ludllm viz runs/alpha --open
```

## Use it inside Claude Code (plugin)

LudLLM ships as a Claude Code plugin that drives the whole pipeline
conversationally, so you never have to type a command:

```
/plugin marketplace add devsandip/ludLLM   # this public repo
/plugin install ludllm@ludllm
/ludllm:ludllm-setup                    # one-time: keys + install check
/ludllm:write-spy-novel                 # explains the pipeline and writes a book with you
```

## Real models

The core is dependency-light (Pydantic) and runs on mock models. Live prose is an
opt-in extra:

```bash
uv sync --extra models     # adds Anthropic (prose) + Google Gemini / OpenAI (cross-family critique)
cp .env.example .env        # add your keys
```

A different model family must critique than drafts, so no model grades its own
homework.

## Development

```bash
uv sync --extra dev
uv run pytest -q
uv run ruff check src tests
```

## License

MIT. See [LICENSE](LICENSE).
