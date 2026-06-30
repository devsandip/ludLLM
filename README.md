# LudLLM

An agentic pipeline that writes a full-length novel end to end. The experiment:
how far a generation-plus-judgment loop can be pushed over 80k+ words while
staying coherent and not reading like a machine wrote it.

The thesis: word production is not the bottleneck. Coherence and taste are. The
architecture exists to protect those two.

## Try it yourself

Two ways in.

Inside Claude Code, use the plugin and never type a pipeline command. It runs the
stages, shows you each result, and waits for your approval:

```
/plugin marketplace add devsandip/LudLLM
/plugin install ludllm@ludllm
/ludllm:ludllm-setup          # one-time: keys + install check
/ludllm:write-spy-novel       # explains the pipeline and writes a book with you
```

Or run it locally. The first run uses mock models, so it needs no keys and costs
nothing:

```bash
git clone https://github.com/devsandip/LudLLM
cd LudLLM
uv sync                              # needs uv
uv run ludllm demo ./out             # builds the bundled example on mock models, no keys
uv run ludllm show ./out/book_state.json
```

To open the interactive studio on a sample, or to write with real models:

```bash
uv sync --extra models               # prose + cross-family critique + pymupdf (dossier pages)
uv run ludllm viz runs/alpha --open  # build and open the story-graph studio for a sample
cp .env.example .env                 # add your keys to write your own book
```

A different model family must critique than drafts, so no model grades its own
homework.

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

## The story-graph studio

`ludllm viz runs/<project>` builds a self-contained, interactive view of one
book's knowledge graph into `runs/<project>/viz/studio.html`. Open it in any
browser, no server: a Story Graph tab with chapter-axis views of who knows which
secret and since when, a revealed-only secrets panel, and click-to-open detail
panels for any secret or character; and a Dossiers tab with a card grid and a
paginated dossier viewer. All epistemic logic stays in the engine core; the page
only renders precomputed data. See
[docs/features/story-graph-viz.md](docs/features/story-graph-viz.md). Two finished
sample novels ship under `runs/alpha` and `runs/alpha-v2`, so you can open the
studio on real output right away (see the quickstart above).

## Development

```bash
uv sync --extra dev
uv run pytest -q
uv run ruff check src tests
```

## License

MIT. See [LICENSE](LICENSE).
