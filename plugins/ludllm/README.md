# LudLLM Spy Novel Studio (Claude Code plugin)

A guided front end for [LudLLM](https://github.com/devsandip/LudLLM), the agentic
pipeline that writes a full-length spy novel end to end, human-gated stage by
stage. The plugin is the conversational app; the `ludllm` Python package is the
engine that does the work.

## What you get

Two skills:

- **`/ludllm:ludllm-setup`** - first-run onboarding. Verifies the engine is
  installed, walks you through the model choice (Claude subscription vs metered
  API) and the keys each path needs, and confirms it works with an offline check.
- **`/ludllm:write-spy-novel`** - the guided write. Explains the five-stage
  pipeline, asks for your starting inputs with guidance on what good input looks
  like, then drives the gated loop from scaffold to manuscript, stopping for your
  approval after every stage.

## Install

```
/plugin marketplace add devsandip/LudLLM
/plugin install ludllm@ludllm
```

Then run `/ludllm:ludllm-setup` once, and `/ludllm:write-spy-novel` whenever you
want to start or continue a book.

## How it relates to the engine

Installing the plugin gives you the skills (the guidance). The skills drive the
`ludllm` CLI, which you install separately from the LudLLM repo:

```
git clone https://github.com/devsandip/LudLLM.git && cd LudLLM
uv sync --extra models
```

The setup skill walks you through this if the `ludllm` command is not found.

## Cost

A full setup (normalize through outline) is roughly $0.25-0.45 on the metered API,
or subscription usage on the default path. A full draft (~40 chapters) is roughly
$10-40 metered. The critic (Gemini) adds cheap cross-family calls. The offline
`ludllm demo` costs nothing.
