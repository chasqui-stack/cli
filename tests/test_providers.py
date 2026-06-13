"""Provider → LangChain integration package wiring (cli#1).

The generated core resolves LLM_PROVIDER / EMBEDDING_PROVIDER at runtime; any
non-Google choice needs its `langchain-<provider>` package installed or the
core ImportErrors on the first turn. The wizard must install it at provision
time.
"""

from chasqui import provision
from chasqui.secrets_gen import GeneratedSecrets
from chasqui.wizard import (
    CORE_BUNDLED_PROVIDER_PACKAGES,
    EMBEDDING_PROVIDERS,
    LLM_PROVIDERS,
    PROVIDER_PACKAGES,
    default_answers,
    provider_packages,
)


def test_every_offered_provider_maps_to_a_package():
    """No wizard choice may be missing from PROVIDER_PACKAGES (the gap bug)."""
    for provider in LLM_PROVIDERS:
        assert provider in PROVIDER_PACKAGES, f"LLM {provider} has no package"
    for provider in EMBEDDING_PROVIDERS:
        assert provider in PROVIDER_PACKAGES, f"embeddings {provider} missing"


def test_google_default_needs_nothing_extra():
    a = default_answers("demo")  # google LLM + google embeddings
    assert provider_packages(a) == []


def test_openai_llm_and_embeddings_dedupes_to_one_package():
    a = default_answers("demo")
    a.llm_provider = "openai"
    a.embedding_provider = "openai"
    assert provider_packages(a) == ["langchain-openai"]


def test_mixed_providers_collects_both():
    a = default_answers("demo")
    a.llm_provider = "anthropic"  # langchain-anthropic
    a.embedding_provider = "openai"  # langchain-openai
    assert provider_packages(a) == ["langchain-anthropic", "langchain-openai"]


def test_openrouter_reuses_the_openai_package():
    a = default_answers("demo")
    a.llm_provider = "openrouter"
    a.embedding_provider = "google"  # bundled — dropped
    assert provider_packages(a) == ["langchain-openai"]


def test_anthropic_llm_with_google_embeddings_drops_the_bundled_one():
    a = default_answers("demo")
    a.llm_provider = "anthropic"
    a.embedding_provider = "google"
    assert provider_packages(a) == ["langchain-anthropic"]
    # langchain-google-genai is bundled and must never be re-added
    assert "langchain-google-genai" in CORE_BUNDLED_PROVIDER_PACKAGES


def test_plan_omits_the_uv_add_step_for_google_default():
    a = default_answers("demo")
    titles = [s.title for s in provision.plan(a, GeneratedSecrets())]
    assert not any(t.startswith("Install provider packages") for t in titles)


def test_plan_adds_uv_add_step_for_ollama():
    a = default_answers("demo")
    a.llm_provider = "ollama"
    a.embedding_provider = "ollama"
    steps = provision.plan(a, GeneratedSecrets())
    add_steps = [s for s in steps if s.title.startswith("Install provider packages")]
    assert len(add_steps) == 1
    step = add_steps[0]
    assert step.argv == ["uv", "add", "langchain-ollama"]
    assert step.cwd == "core"
    assert step.needs == ["Install core dependencies (uv sync)"]
