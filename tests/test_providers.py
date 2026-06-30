"""The provider adapters import without their SDKs installed (lazy imports), so
the core stays lean. Constructing one is what pulls the SDK in; we don't do that
here (no keys, no network, no cost)."""

from __future__ import annotations

import importlib


def test_providers_module_imports_without_sdks():
    mod = importlib.import_module("ludllm.models.providers")
    assert mod.AnthropicModel.family == "anthropic"
    assert mod.GeminiModel.family == "google"
    assert mod.OpenAIModel.family == "openai"
    assert hasattr(mod, "default_bundle")


def test_adapters_satisfy_the_chat_model_shape():
    from ludllm.models.providers import AnthropicModel, GeminiModel, OpenAIModel

    for cls in (AnthropicModel, GeminiModel, OpenAIModel):
        assert hasattr(cls, "generate")
        assert hasattr(cls, "family")
