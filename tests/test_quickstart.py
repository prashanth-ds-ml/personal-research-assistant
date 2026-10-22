"""scripts/setup.py and scripts/start.py: the two-command quick start (tool checks, settings files, start commands)."""
import importlib.util
import io
import json
import pathlib
import types

import pytest

SCRIPTS = pathlib.Path(__file__).parent.parent / "scripts"


def load(name):
    spec = importlib.util.spec_from_file_location(f"quickstart_{name}", SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


setup = load("setup")
start = load("start")


def fake_run(version):
    return lambda cmd, **kw: types.SimpleNamespace(stdout=version, returncode=0)


def test_node_version_parsing():
    assert setup.node_version("v24.15.0\n") == (24, 15) and setup.node_version("22.18.1") == (22, 18)
    assert setup.node_version("garbage") is None


def test_missing_tools_are_named_with_where_to_get_them():
    with pytest.raises(setup.SetupError) as e:
        setup.check_tools(which=lambda n: None if n in ("uv", "ollama") else f"/bin/{n}", run=fake_run("v24.1.0"))
    msg = str(e.value)
    assert "docs.astral.sh/uv" in msg and "ollama.com/download" in msg and "nodejs" not in msg


def test_old_node_is_refused_with_the_version_found():
    with pytest.raises(setup.SetupError) as e:
        setup.check_tools(which=lambda n: f"/bin/{n}", run=fake_run("v20.11.0"))
    assert "22.18" in str(e.value) and "found 20.11" in str(e.value)
    assert setup.check_tools(which=lambda n: f"/bin/{n}", run=fake_run("v22.18.0"))["node"] == "/bin/node"


def test_ollama_not_running_says_how_to_start_it():
    def down(url, timeout):
        raise ConnectionRefusedError
    with pytest.raises(setup.SetupError) as e:
        setup.ollama_models("http://localhost:11434", opener=down)
    assert "not running" in str(e.value) and "ollama serve" in str(e.value)


def test_installed_models_are_read_and_only_missing_ones_pulled():
    body = io.BytesIO(json.dumps({"models": [{"name": "qwen3-embedding:0.6b"}, {"name": "llama3:latest"}]}).encode())
    body.__enter__ = lambda *a: body
    body.__exit__ = lambda *a: None
    installed = setup.ollama_models("http://x", opener=lambda url, timeout: body)
    assert setup.missing_models(installed) == ["qwen3.5:4b"]
    assert setup.missing_models(["qwen3.5:4b", "qwen3-embedding:0.6b:latest"], ["qwen3.5:4b", "qwen3-embedding:0.6b"]) == []


def test_with_values_replaces_only_the_named_settings():
    tpl = "# comment VAULT_PATH=x\nVAULT_PATH=/absolute/path\nRERANK=true\nOTHER=1"
    out = setup.with_values(tpl, {"VAULT_PATH": "/data/desk", "RERANK": "false"})
    assert out == "# comment VAULT_PATH=x\nVAULT_PATH=/data/desk\nRERANK=false\nOTHER=1\n"


def make_repo(tmp_path):
    (tmp_path / "dashboard").mkdir()
    (tmp_path / ".env.example").write_text("VAULT_PATH=/absolute/path/to/your/ObsidianVault\nRERANK=true\n")
    (tmp_path / "dashboard" / ".env.example").write_text("LANGGRAPH_API_URL=http://127.0.0.1:2025\n"
                                                         "VAULT_PATH=/absolute/path/to/your/ObsidianVault\n")
    return tmp_path


def test_settings_are_written_once_and_never_overwritten(tmp_path):
    root = make_repo(tmp_path)
    vault = tmp_path / "My Desk"
    notes = setup.write_settings(vault, rerank=False, root=root)
    assert vault.is_dir() and any("wrote .env" in n for n in notes)
    env = setup.read_env(root / ".env")
    assert env["VAULT_PATH"] == str(vault) and env["RERANK"] == "false"
    assert setup.read_env(root / "dashboard" / ".env.local")["VAULT_PATH"] == str(vault)

    (root / ".env").write_text("VAULT_PATH=/mine\n")                     # the user's own edits survive a second run
    notes = setup.write_settings(tmp_path / "other", rerank=True, root=root)
    assert setup.read_env(root / ".env") == {"VAULT_PATH": "/mine"} and all(n.startswith("kept") for n in notes)


def test_vault_choice_existing_then_flag_then_question(tmp_path):
    args = types.SimpleNamespace(vault=None, yes=False)
    assert setup.choose_vault(args, {"VAULT_PATH": "/kept"}, ask=lambda q: "x") == pathlib.Path("/kept")
    assert setup.choose_vault(args, {"VAULT_PATH": setup.PLACEHOLDER}, ask=lambda q: "") == pathlib.Path.home() / "ResearchDesk"
    assert setup.choose_vault(args, {}, ask=lambda q: str(tmp_path / "d")) == (tmp_path / "d").resolve()
    assert setup.choose_vault(types.SimpleNamespace(vault=None, yes=True), {}, ask=None) == pathlib.Path.home() / "ResearchDesk"


def test_dashboard_steps_are_skipped_when_up_to_date(tmp_path):
    d = tmp_path / "dashboard"
    (d / "src").mkdir(parents=True)
    (d / "package-lock.json").write_text("{}")
    assert setup.needs_npm_ci(d) and setup.needs_build(d)
    (d / "node_modules").mkdir()
    (d / "node_modules" / ".package-lock.json").write_text("{}")
    (d / ".next").mkdir()
    (d / ".next" / "BUILD_ID").write_text("x")
    assert not setup.needs_npm_ci(d) and not setup.needs_build(d)


def test_start_preflight_points_to_setup(tmp_path):
    problems = start.preflight(tmp_path)
    assert len(problems) == 3 and all("scripts/setup.py" in p for p in problems)


def test_start_commands_wire_ports_python_and_utf8(tmp_path):
    c = start.commands(tmp_path, 2099, 3099, {"PATH": "p"})
    assert c["backend"]["cmd"][1:] == ["dev", "--no-browser", "--no-reload", "--port", "2099"]
    assert c["backend"]["env"]["PYTHONUTF8"] == "1" and c["backend"]["url"].endswith(":2099/ok")
    dash = c["dashboard"]
    assert dash["cmd"][-4:] == ["-H", "127.0.0.1", "-p", "3099"] and dash["cwd"] == tmp_path / "dashboard"
    assert dash["env"]["LANGGRAPH_API_URL"] == "http://127.0.0.1:2099"
    assert dash["env"]["PYTHON_BIN"].startswith(str(tmp_path / ".venv")) and dash["env"]["PATH"] == "p"
