"""Real provider adapters: Anthropic (prose + setup), Gemini / OpenAI (critique).

These implement the same `ChatModel` interface as the mocks, so the pipeline is
unchanged. The provider SDKs are imported LAZILY inside each adapter, so this
module imports fine without `ludllm[models]` installed and the core stays lean
and key-free. Constructing an adapter is what pulls the SDK in.

Model routing follows the project's own cost decision (docs/decisions): draft and
author on Sonnet (cost-effective for ~130k words), extract on Haiku (cheap,
mechanical), critique cross-family on Gemini. Every model id is env-overridable;
point the drafter at Opus for hero chapters when you want.

Nothing here runs until you provide keys (see .env.example) and call the model.
"""

from __future__ import annotations

import os

# Defaults. Anthropic ids are current; Gemini/OpenAI ids vary by release, so
# they default to a sensible value but are meant to be set via env.
_DRAFTER_DEFAULT = "claude-sonnet-4-6"
_AUTHOR_DEFAULT = "claude-sonnet-4-6"
_EXTRACTOR_DEFAULT = "claude-haiku-4-5"
_GEMINI_DEFAULT = "gemini-2.5-flash"
_OPENAI_DEFAULT = "gpt-5.1"


class AnthropicModel:
    """Anthropic adapter. Caches the (stable) system prompt: the bible/ledger
    slice is re-read on every pass, which is exactly what caching is for."""

    family = "anthropic"

    def __init__(
        self,
        model: str | None = None,
        *,
        name: str | None = None,
        max_tokens: int = 8000,
        cache_system: bool = True,
    ) -> None:
        import anthropic  # lazy: keeps core import key-free

        self._client = anthropic.Anthropic()
        self.model = model or os.environ.get("ANTHROPIC_MODEL", _DRAFTER_DEFAULT)
        self.name = name or self.model
        self.max_tokens = max_tokens
        self.cache_system = cache_system

    def generate(
        self, *, system: str, prompt: str, task: str | None = None, max_tokens: int | None = None
    ) -> str:
        system_block = [{"type": "text", "text": system}]
        if self.cache_system:
            system_block[0]["cache_control"] = {"type": "ephemeral"}
        # Stream and accumulate. The SDK refuses a non-streaming request whose
        # estimated runtime exceeds 10 minutes, which a large max_tokens (e.g. the
        # 32k outline) trips; streaming is the SDK's supported path for long
        # generations and keeps the connection alive. Caching still applies.
        with self._client.messages.stream(
            model=self.model,
            max_tokens=max_tokens or self.max_tokens,
            system=system_block,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            resp = stream.get_final_message()
        return "".join(b.text for b in resp.content if b.type == "text")


# Tools the headless CLI must not run: every setup/prose call is a pure
# completion, so block the agent's file/shell/search/task tools. Disallowing
# only blocks execution, not schema loading, so it does not remove the overhead;
# it just guarantees the call cannot wander off and touch the repo.
_CLI_DISALLOWED_TOOLS = [
    "Bash", "Read", "Edit", "Write", "WebSearch", "WebFetch",
    "Glob", "Grep", "Task", "TodoWrite", "NotebookEdit",
]


class ClaudeCodeModel:
    """Routes generation through the local Claude Code CLI in headless mode
    (`claude -p`), so calls run on the user's Claude Code subscription instead of
    the metered Anthropic API. Same family as `AnthropicModel` ("anthropic"), so
    a Gemini critic still satisfies the cross-family critique rule.

    Why reach for it: zero metered spend, and the CLI's 64k output cap, so the
    large setup-stage JSON (world bible + ledger, cast, outline) does not truncate
    the way an 8k API budget can.

    The cost: every headless call carries Claude Code's own harness overhead
    (~20k input tokens of agent prompt + tool schemas) that a bare API call does
    not, even with the system prompt overridden and MCP/tools stripped. Cheap for
    the handful of setup stages; for a long unattended book write it burns
    subscription usage fast and can hit rate limits. This is the DEFAULT path;
    opt back to the metered API adapter with LUDLLM_USE_CLAUDE_CLI=0 (see
    `_use_claude_cli`). `max_tokens` is accepted for interface parity but ignored
    (the CLI sets its own, larger, cap)."""

    family = "anthropic"

    def __init__(
        self, model: str | None = None, *, name: str | None = None, timeout: int = 900
    ) -> None:
        self.model = model or os.environ.get("ANTHROPIC_MODEL", _DRAFTER_DEFAULT)
        self.name = name or self.model
        self.timeout = timeout

    def generate(
        self, *, system: str, prompt: str, task: str | None = None, max_tokens: int | None = None
    ) -> str:
        import json
        import subprocess

        # Force subscription auth: if ANTHROPIC_API_KEY is in the environment the
        # CLI bills the metered API instead of the Claude Code plan, which defeats
        # the entire point of this adapter.
        env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
        cmd = [
            "claude", "-p",
            "--model", self.model,
            "--output-format", "json",
            "--system-prompt", system,
            "--strict-mcp-config",  # ignore session MCP servers; no tool-schema bloat from them
            "--disallowed-tools", *_CLI_DISALLOWED_TOOLS,  # variadic: keep this flag last
        ]
        try:
            proc = subprocess.run(
                cmd, input=prompt, env=env, capture_output=True, text=True, timeout=self.timeout
            )
        except FileNotFoundError as e:
            raise RuntimeError(
                "claude CLI not found on PATH; LUDLLM_USE_CLAUDE_CLI requires Claude Code installed"
            ) from e
        if proc.returncode != 0:
            raise RuntimeError(f"claude CLI exit {proc.returncode}: {proc.stderr.strip()[:600]}")
        try:
            envelope = json.loads(proc.stdout)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"claude CLI returned non-JSON output: {proc.stdout[:300]}") from e
        if envelope.get("is_error"):
            raise RuntimeError(f"claude CLI reported error: {str(envelope.get('result', ''))[:600]}")
        return envelope.get("result", "")


class GeminiModel:
    """Google Gemini adapter (cross-family critic). Reads GEMINI_API_KEY."""

    family = "google"

    def __init__(self, model: str | None = None, *, name: str | None = None) -> None:
        from google import genai  # lazy

        self._client = genai.Client()
        self.model = model or os.environ.get("GEMINI_MODEL", _GEMINI_DEFAULT)
        self.name = name or self.model

    def generate(
        self, *, system: str, prompt: str, task: str | None = None, max_tokens: int | None = None
    ) -> str:
        from google.genai import types

        resp = self._client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=types.GenerateContentConfig(system_instruction=system),
        )
        return resp.text or ""


class OpenAIModel:
    """OpenAI adapter (tie-break critic / blind-reader eval). Reads OPENAI_API_KEY."""

    family = "openai"

    def __init__(self, model: str | None = None, *, name: str | None = None) -> None:
        from openai import OpenAI  # lazy

        self._client = OpenAI()
        self.model = model or os.environ.get("OPENAI_MODEL", _OPENAI_DEFAULT)
        self.name = name or self.model

    def generate(
        self, *, system: str, prompt: str, task: str | None = None, max_tokens: int | None = None
    ) -> str:
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        )
        return resp.choices[0].message.content or ""


def _use_claude_cli() -> bool:
    """Whether to route Anthropic-family calls through the Claude Code CLI (the
    user's subscription) rather than the metered API.

    Default is the subscription: LudLLM is a personal authoring tool, and the
    subscription is the cheaper path for the operator who already pays for it.
    Opt back to the metered API with LUDLLM_USE_CLAUDE_CLI=0 (or false/no/off) —
    needed in any environment without the `claude` CLI on PATH (CI, a bare
    checkout) or when you deliberately want metered, key-based billing."""
    val = os.environ.get("LUDLLM_USE_CLAUDE_CLI")
    if val is None or val.strip() == "":
        return True  # unset -> subscription is the default
    return val.strip().lower() in ("1", "true", "yes", "on")


def default_bundle():
    """The default cross-family routing. Requires `ludllm[models]` + keys.

    Drafter/author on Sonnet, extractor on Haiku, critic on Gemini (different
    family from the drafter, so the critique assertion passes). Override any id
    via ANTHROPIC_MODEL / LUDLLM_*_MODEL / GEMINI_MODEL env vars.

    By default the Anthropic-family calls (drafter/author/extractor) run through
    the local Claude Code CLI on the user's subscription, not the metered API
    (see `_use_claude_cli`). Set LUDLLM_USE_CLAUDE_CLI=0 to opt back to the
    metered, key-based API (needed where the `claude` CLI is absent, e.g. CI).
    The critic stays on Gemini either way, so cross-family critique still holds.
    See `ClaudeCodeModel` for the trade-off (no metered spend and a 64k output
    cap, but per-call harness overhead and subscription rate limits)."""
    from ludllm.models.base import ModelBundle

    use_cli = _use_claude_cli()
    anthropic_cls = ClaudeCodeModel if use_cli else AnthropicModel

    drafter = anthropic_cls(os.environ.get("LUDLLM_DRAFTER_MODEL", _DRAFTER_DEFAULT), name="drafter")
    author = anthropic_cls(os.environ.get("LUDLLM_AUTHOR_MODEL", _AUTHOR_DEFAULT), name="author")
    extractor = anthropic_cls(
        os.environ.get("LUDLLM_EXTRACTOR_MODEL", _EXTRACTOR_DEFAULT), name="extractor"
    )
    # Cross-family critic. Gemini by default; LUDLLM_CRITIC_PROVIDER=openai swaps to GPT
    # (e.g. when the Gemini key is rate-limited). Either is a different family from the
    # Anthropic drafter/author, so the cross-family critique rule holds.
    if os.environ.get("LUDLLM_CRITIC_PROVIDER", "gemini").strip().lower() == "openai":
        critic = OpenAIModel(name="critic")
    else:
        critic = GeminiModel(name="critic")
    return ModelBundle(drafter=drafter, extractor=extractor, critic=critic, author=author)
