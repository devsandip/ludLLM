---
name: ludllm-setup
description: First-run setup for LudLLM, the spy-novel authoring engine. Verifies the engine is installed, walks the user through the model choice (Claude subscription vs metered API) and the keys each path needs, then confirms everything works with an offline check. Use when the user installs LudLLM, says "set up ludllm" or "get me started", hits a missing-command or missing-key error, or before the first novel run on a fresh machine.
allowed-tools: Bash Read Edit Write
---

# LudLLM setup

Your job: get the user from "just installed the plugin" to "ready to write a
novel" with the fewest steps. Detect what is already in place and only walk
through the gaps. Be concrete, run the checks yourself, and report plainly.

The plugin is the front end (this guidance). The **engine** is the `ludllm`
Python package, which lives in the LudLLM git repo and does the real work. Setup
bridges the two.

Work through these in order. Stop and ask only when you genuinely need the user.

## 1. Is the engine installed?

Run `ludllm --help` (or `uv run ludllm --help` if you are inside the repo).

- **It works** -> the engine is installed. Skip to step 2.
- **Command not found** -> the user has the plugin but not the engine. Guide them:
  1. Clone it: `git clone https://github.com/devsandip/LudLLM.git && cd LudLLM`
  2. Install with real-model support: `uv sync --extra models`
     (uv is the package manager; if missing, point them to https://docs.astral.sh/uv/).
  3. From here on, run engine commands as `uv run ludllm ...` from the repo root,
     or activate the venv so `ludllm` is on PATH.

  Everything below assumes commands run from the repo root.

## 2. Pick the model path, then set only the keys it needs

LudLLM runs Anthropic-family models to draft/author/extract, and a **different**
family (Gemini or OpenAI) to critique. The critic must never be Claude, that is a
hard rule, so a Gemini key is always required. The Claude side has two paths.

Explain this choice to the user in one short pass, then set up whichever they pick.
Default and recommendation: **the subscription path** (no per-token spend).

**Path A: Claude Code subscription (default, recommended).**
- The Anthropic calls run through the local `claude` CLI on the user's
  subscription. No `ANTHROPIC_API_KEY` needed and no metered Anthropic spend.
- Requires the `claude` CLI installed and logged in. Verify: run `claude --version`.
  If missing, point to the Claude Code install docs; if installed but not logged
  in, have them run `claude` once interactively to authenticate.
- Nothing to set: this is the default as of the current build. (`LUDLLM_USE_CLAUDE_CLI`
  unset or `1` selects it.)

**Path B: Metered Anthropic API.**
- Bills per token against an API key. Use this in CI, or on a machine with no
  `claude` CLI.
- Set in `.env`: `LUDLLM_USE_CLAUDE_CLI=0` and `ANTHROPIC_API_KEY=sk-ant-...`
  (get a key at https://console.anthropic.com/).

**The critic key (always required, both paths).**
- `GEMINI_API_KEY=...` (get one at https://aistudio.google.com/apikey). Gemini is
  the default cross-family critic.
- Optional: `OPENAI_API_KEY=...` plus `LUDLLM_CRITIC_PROVIDER=openai` to use GPT as
  the critic instead (e.g. if Gemini is rate-limited). OpenAI is also used for
  cover-image generation if the user wants one later.

**Writing the keys.** Keys live in `.env` at the repo root, which is gitignored,
never commit it. If `.env` does not exist, copy `.env.example` to `.env` first
(`cp .env.example .env`), then read it and fill the relevant lines. Always read
`.env` before editing so you do not clobber an existing key. Never echo a full key
back to the user; confirm by name ("GEMINI_API_KEY is set") only.

## 3. Confirm it works (offline, no cost)

Run `ludllm demo`. It writes a tiny book end to end on **mock** models, no keys,
no tokens. If it completes, the engine is wired correctly. Report what it wrote.

If the user is on Path A, that demo does not exercise the subscription. You can
optionally confirm the real path with one cheap real call later (the first novel's
`normalize` stage is the natural place), but do not burn tokens during setup
unless the user asks.

## 4. Report and hand off

Summarize the resolved state in three lines: engine installed (yes), model path
(subscription / API), critic (Gemini / OpenAI), and any key still missing. Then
point the user at the next step:

> Setup looks good. When you are ready to write, run **/ludllm:write-spy-novel**
> and I will explain the process and ask for your starting inputs.

If a key is still missing, say exactly which one and how to get it, and stop there.
