---
name: write-spy-novel
description: Guide the user through writing a full-length spy novel with LudLLM, end to end. Explains the five-stage pipeline in plain language, elicits the starting inputs (premise, the secret/betrayal spine, locked characters, length and tone) with concrete guidance on what good input looks like, then drives the human-gated stage loop from scaffold to manuscript. Use when the user wants to start a new spy novel, says "write me a spy novel about X", "start a new book", or wants to run or continue a stage.
allowed-tools: Bash Read Edit Write
---

# Write a spy novel with LudLLM

You are the showrunner's assistant. LudLLM generates; the human approves. Your job
is to explain the process, get strong starting inputs, and then drive the pipeline
one gated stage at a time, stopping for review after every stage. Never
auto-advance the book.

Run engine commands as `ludllm ...` from the repo root (or `uv run ludllm ...`).

## 0. Preflight

Confirm the engine is ready: run `ludllm status` or `ludllm --help`. If the command
is missing or a key is unset, stop and route the user to **/ludllm:ludllm-setup**
first. Do not start a book on a half-configured machine.

## 1. Explain the process (once, briefly)

Tell the user, in plain language, how a book gets made. Keep it to this shape:

> We build the book in five setup stages, then write it. After each stage I show
> you the result and a critic's scorecard, and we stop so you can approve or change
> it before moving on. Nothing advances without your say-so.
>
> 1. **Normalize** - I turn your brief into a clean, structured premise.
> 2. **World** - the setting, the plot mechanism, real-world grounding, the era
>    timeline, and the secrets ledger (who hides what, and when it gets revealed).
> 3. **Cast** - the roster and what each character believes, including the false
>    beliefs the plot runs on.
> 4. **Structure** - point of view, time handling, the acts, the spy tropes in
>    play, and where each secret gets revealed.
> 5. **Outline** - chapter by chapter: POV, beats, hooks, and the reader-vs-
>    character information gap.
>
> Then the **writer** drafts the chapters, pausing at each act boundary for a
> checkpoint. A full setup costs about a dollar; the full draft is roughly $10-40
> on the metered API, or subscription usage if you are on that path.

Then move to inputs.

## 2. Elicit the starting inputs (the important part)

Ask for these. For each, say what good input looks like and give a quick
good-vs-weak contrast so the user is not staring at a blank prompt. Collect them
conversationally; you do not need every field, but premise and the secret spine
carry the book.

**A. Premise (required).** A short paragraph, not a one-liner. It should name the
setting and era, the operation or threat, and the protagonist's position inside it.
- Strong: "1986, divided Berlin. A burned-out MI6 handler is ordered to run a
  walk-in who claims the Stasi have a mole inside the Station, knowing the walk-in
  may be the bait in a trap built to expose her own past."
- Weak: "A spy has to stop the bad guys." (No era, no specific operation, no
  protagonist position. This produces a generic book.)

**B. The secret / betrayal spine (the load-bearing input).** Spy novels run on
who-knows-what. Get: *who hides what*, and *when the reader vs the protagonist
should learn it*. This is what the secrets ledger binds reveals to; without it the
book is flat.
- Strong: "The handler's late mentor was the original mole; she does not know.
  The reader should suspect by the midpoint; she should learn it only in the final
  act, from the one person she trusted."
- Weak: "There's a twist at the end." (No content, no timing, nothing to bind.)
- If the user has no secret in mind, help them invent one before scaffolding. Offer
  two or three options grounded in their premise and let them pick.

**C. Locked characters (optional).** Anyone who must exist, one line each: name,
role, and one defining tension.
- Example: "Marta Reyes, the Station's analyst, secretly feeding the protagonist
  intel against orders."
- If none, the cast stage invents the roster; that is fine.

**D. Length and tone (optional but useful).** A chapter count or word target, plus
two or three tonal touchstones.
- Example: "About 40 chapters, ~80k words. le Carre interiority, not Bourne
  kinetics. Cold, procedural, morally grey."

**E. Era / time mode (optional).** Single period, or a braided timeline across two
eras? This drives the structure stage. If the premise implies a single era, assume
that and say so; only ask if it is genuinely ambiguous.

Restate what you heard in a few lines before scaffolding, so the user can correct
you cheaply before any tokens are spent.

## 3. Scaffold the project

Create it: `ludllm new "<premise paragraph>" --name "<title>"`. The folder is the
title slug under `runs/`. Confirm it was created and show the path.

## 4. Drive the gated stage loop

Run the stages one at a time: **normalize -> world -> cast -> structure -> outline**.
For each stage:

1. **Check params first.** Run `ludllm params runs/<proj>` and show the user only
   the knobs relevant to this stage (setup stages: `critique.mode`,
   `critique.enabled`, `critique.auto_revise_passes`). Ask whether to keep or
   change them. To change one, read `runs/<proj>/params.toml`, edit it, confirm
   with `ludllm params`. Skip this if the user already set params this session and
   has not asked to revisit.

2. **Run it:** `ludllm stage runs/<proj> <stage>`. This calls the real models,
   renders the markdown, and runs the critique panel (a cross-family critic scores
   a per-stage rubric; the verdict is ship / tighten / regenerate and renders as a
   scorecard on top of the stage markdown). In the default `auto_revise` mode, a
   non-ship verdict triggers one regenerate-and-recritique pass before you see it.

3. **Show the user the rendered files and the scorecard**, then **stop and wait for
   approval.** The critique is advisory; the human is the gate. The stage outputs:
   - world -> `01_world/world.md` and `01_world/ledger.md`
   - cast -> `02_cast/cast.md`
   - structure -> `03_structure/structure.md`
   - outline -> `04_outline/outline.md` and `04_outline/timeline.md`

4. **Take edits through any channel and reconcile into the JSON.**
   `book_state.json` is the single source of truth and is Pydantic-validated; the
   markdown is a generated view. Always read a file before editing it.
   - User asks in chat ("move the reveal to chapter 8", "cut the analyst"): read
     `book_state.json`, edit it, then `ludllm render runs/<proj>`, and show what
     changed. This is the cheap redo: no model call.
   - User edited a markdown file or the JSON directly: reconcile / re-render and
     confirm it still loads.
   - "Regenerate with my notes" is the expensive redo:
     `ludllm stage runs/<proj> <stage> --force` re-runs on the model and
     invalidates downstream stages.

5. Only advance to the next stage once the user approves.

Use `ludllm status runs/<proj>` anytime to show stage progress and checks.

## 5. Write the book

Once the outline is approved, run the writer stage. It drafts chapters to
`runs/<proj>/05_manuscript/`, pausing at each act boundary for a checkpoint. Use
the repo's full-book runner if one exists (`scripts/write_book.py`, or
`scripts/run_alpha_v2.py`); otherwise build a small runner that scaffolds the
setup gated, then loops chapters with act-boundary stops, before a long unattended
write. The writer needs only the outline; do not build dossiers or the studio yet.
Writer params worth surfacing: `writer.max_revise`, `writer.retries`,
`writer.advisory`.

## 6. Finish the book: dossiers and the story graph (mandatory, run last)

When every chapter is accepted, run the two off-spine finishing stages on the FINAL
book. They run last because the chapter loop mutates state while writing, so an
earlier build would be stale. They are mandatory: the book is not finished without
them, and `ludllm status` shows a "Finishing stages" line.

- `ludllm stage runs/<proj> dossier` builds the per-character classified files
  (the redactions are bound to the secret ledger).
- `ludllm stage runs/<proj> viz` builds the interactive story-graph studio at
  `runs/<proj>/viz/studio.html`: a browser view of who knows which secret and
  since when, with a Story Graph tab (three chapter-axis views: Knowledge, a
  3-chapter window, and Propagation) and a Dossiers tab. It is model-free and
  read-only.

The full-book runner (`scripts/write_book.py`) runs both automatically once the
manuscript is complete. Run viz after dossier so its Dossiers tab is populated, then
show the user the studio. The Story Graph tab needs only the outline, so you can also
run the `ludllm viz` alias mid-write to peek at the asymmetry; re-run it any time.

## Non-negotiables

- **The human is the gate.** Never auto-advance the real book. Stop for review at
  every stage.
- **`book_state.json` is canonical and validated.** Markdown is a generated view.
  Reconcile edits into the JSON, then re-render. Do not treat markdown as truth.
- **The critic is a different model family from the author** (Gemini critiques
  Claude). This holds for the prose critic and the dimensional panel. Do not break
  it.
- **The critique panel is advisory.** It informs the human gate; it never replaces
  it or rewrites the book on its own.
- Do not use a real film's plot or trademarked character names.
- Never commit `.env` or `runs/` (both gitignored). Never echo API keys.
