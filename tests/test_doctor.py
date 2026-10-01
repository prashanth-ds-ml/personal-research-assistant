"""The setup check, offline: a fake Ollama and fake machine readings."""

import httpx

from research_assistant import doctor as d


def http_with(models):
    def handler(request):
        return httpx.Response(200, json={"models": [{"name": m} for m in models]})
    return httpx.Client(transport=httpx.MockTransport(handler))


ENV = {"LOCAL_LLM": "llama3.1:8b", "WRITER_MODEL": "gemma4:e4b", "EMBEDDING_MODEL": "ollama:qwen3-embedding:0.6b"}


def test_required_models_come_from_the_settings():
    assert d.required_models(ENV) == {"llama3.1:8b": "planning and extraction", "gemma4:e4b": "writing the report",
                                      "qwen3-embedding:0.6b": "search embeddings"}
    assert set(d.required_models({})) == {"llama3.2", "qwen3-embedding:0.6b"}          # defaults: one chat model plus embeddings


def test_missing_models_are_listed_with_the_command_to_pull_them():
    checks = d.check_ollama("http://x", ENV, http_with(["llama3.1:8b", "qwen3-embedding:0.6b:latest"]))
    by = {c.name: c for c in checks}
    assert by["Ollama"].status == d.OK and by["Model llama3.1:8b"].status == d.OK
    assert by["Model qwen3-embedding:0.6b"].status == d.OK                              # ":latest" suffix is accepted
    assert by["Model gemma4:e4b"].status == d.FAIL and by["Model gemma4:e4b"].fix == "ollama pull gemma4:e4b"


def test_a_stopped_ollama_is_one_clear_failure():
    def boom(request):
        raise httpx.ConnectError("refused")

    checks = d.check_ollama("http://localhost:11434", ENV, httpx.Client(transport=httpx.MockTransport(boom)))
    assert len(checks) == 1 and checks[0].status == d.FAIL and "ollama.com" in checks[0].fix


def test_vault_checks(tmp_path):
    assert d.check_vault("").status == d.FAIL
    assert d.check_vault("/absolute/path/to/your/ObsidianVault").status == d.FAIL           # the .env.example placeholder
    assert d.check_vault(str(tmp_path / "missing")).status == d.WARN
    assert d.check_vault(str(tmp_path)).status == d.OK


def test_env_file_check(tmp_path):
    assert d.check_env_file(tmp_path).status == d.FAIL
    (tmp_path / ".env").write_text("X=1", encoding="utf-8")
    assert d.check_env_file(tmp_path).status == d.OK


def test_memory_and_ports_and_gpu_warn_but_do_not_fail():
    assert d.check_memory(1.6).status == d.WARN and d.check_memory(9.0).status == d.OK and d.check_memory(None).status == d.WARN
    assert d.check_port(2025, "backend", in_use=lambda p: False).status == d.WARN
    assert d.check_port(2025, "backend", in_use=lambda p: True).status == d.OK
    assert d.check_gpu(lambda: ("RTX", 10.0, 80.0)).status == d.WARN                         # the power cap we actually met
    assert d.check_gpu(lambda: ("RTX", 115.0, 80.0)).status == d.OK
    assert d.check_gpu(lambda: None).status == d.WARN                                          # no GPU at all
    assert d.check_gpu(lambda: ("RTX", None, 80.0)).status == d.OK                              # GPU found, limit not reported


def test_render_summarises_and_shows_fixes():
    text = d.render([d.Check("A", d.OK, "fine"), d.Check("B", d.FAIL, "broken", "do this"), d.Check("C", d.WARN, "meh", "try that")])
    assert "[FAIL] B: broken" in text and "-> do this" in text and "1 problem(s) to fix, 1 warning(s)." in text
    assert d.render([d.Check("A", d.OK, "fine")]).endswith("Everything needed is in place.")
