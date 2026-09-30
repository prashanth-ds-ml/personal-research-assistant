"""Configuration precedence and what a caller of the API is allowed to change per run."""

import pytest

from research_assistant.configuration import PER_RUN_KEYS, Configuration

SENSITIVE = ["vault_path", "kb_path", "library_folders", "docs_path", "ollama_base_url", "lmstudio_base_url",
             "sources_subdir", "research_subdir", "profile_note_path", "embedding_model"]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in Configuration.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)


def cfg(configurable=None):
    return Configuration.from_runnable_config({"configurable": configurable or {}})


def test_precedence_is_env_then_per_run_then_default(monkeypatch):
    assert cfg().max_web_research_loops == 3                                  # default
    assert cfg({"max_web_research_loops": 5}).max_web_research_loops == 5     # per run beats default
    monkeypatch.setenv("MAX_WEB_RESEARCH_LOOPS", "7")
    assert cfg({"max_web_research_loops": 5}).max_web_research_loops == 7     # env beats per run


def test_an_empty_environment_variable_counts_as_unset(monkeypatch):
    monkeypatch.setenv("PLANNER_MODEL", "")          # what docker-compose passes for an unset option
    assert cfg({"planner_model": "gemma4:e4b"}).planner_model == "gemma4:e4b"
    monkeypatch.setenv("PLANNER_MODEL", "llama3.1:8b")
    assert cfg({"planner_model": "gemma4:e4b"}).planner_model == "llama3.1:8b"


@pytest.mark.parametrize("key", SENSITIVE)
def test_paths_and_service_urls_cannot_be_set_per_run(key):
    default = getattr(cfg(), key)
    assert getattr(cfg({key: "C:/somewhere/else"}), key) == default
    assert key not in PER_RUN_KEYS


def test_the_environment_can_still_set_them(monkeypatch):
    monkeypatch.setenv("LIBRARY_FOLDERS", "C:/lib")
    monkeypatch.setenv("VAULT_PATH", "C:/vault")
    assert cfg().library_folders == "C:/lib" and cfg().vault_path == "C:/vault"


def test_the_options_the_dashboard_sends_are_allowed():
    sent = {"collect_sources": True, "seed_urls": "https://a.example", "max_web_research_loops": 2,
            "search_api": "local_docs"}
    c = cfg(sent)
    assert c.collect_sources is True and c.seed_urls == "https://a.example" and c.search_api == "local_docs"
    assert set(sent) <= PER_RUN_KEYS


def test_every_per_run_key_is_a_real_field():
    assert PER_RUN_KEYS <= set(Configuration.model_fields)
