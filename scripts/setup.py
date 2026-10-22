"""One-time setup: everything a fresh clone needs, in order, with a plain-language fix for anything missing.

  uv run scripts/setup.py                 asks one question (where to keep your research), then sets up the rest
  uv run scripts/setup.py --yes           no questions: research folder ~/ResearchDesk (or --vault PATH)
  uv run scripts/setup.py --no-rerank     skip PyTorch/transformers (smaller install); sets RERANK=false

Steps: check uv, Node.js and Ollama -> install the Python packages at the tested versions (uv.lock) -> pull the two
Ollama models -> write .env and dashboard/.env.local (existing files are kept) -> install and build the dashboard at the
tested versions (package-lock.json) -> run the setup check. Safe to run again: finished steps are skipped.
Standard library only, because it runs before the packages are installed.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DASHBOARD = ROOT / "dashboard"
MODELS = ["qwen3.5:4b", "qwen3-embedding:0.6b"]
NODE_MIN = (22, 18)
PLACEHOLDER = "/absolute/path/to/your/ObsidianVault"


class SetupError(Exception):
    """A step that cannot continue; the message says what to do."""


def say(msg: str = "") -> None:
    print(msg, flush=True)


def step(n: int, title: str) -> None:
    say(f"\n[{n}/6] {title}")


def node_version(text: str) -> tuple[int, int] | None:
    """'v24.15.0' -> (24, 15)."""
    m = re.match(r"v?(\d+)\.(\d+)", text.strip())
    return (int(m.group(1)), int(m.group(2))) if m else None


def check_tools(which=shutil.which, run=subprocess.run) -> dict[str, str]:
    """Paths of uv, node, npm and ollama, or a SetupError naming what to install."""
    missing = []
    found = {name: which(name) for name in ("uv", "node", "npm", "ollama")}
    if not found["uv"]:
        missing.append("uv: https://docs.astral.sh/uv/getting-started/installation/")
    if not found["node"] or not found["npm"]:
        missing.append(f"Node.js {NODE_MIN[0]}.{NODE_MIN[1]} or newer: https://nodejs.org")
    else:
        v = node_version(run([found["node"], "--version"], capture_output=True, text=True).stdout)
        if v is None or v < NODE_MIN:
            found_v = f"{v[0]}.{v[1]}" if v else "an unknown version"
            missing.append(f"Node.js {NODE_MIN[0]}.{NODE_MIN[1]} or newer (found {found_v}): https://nodejs.org")
    if not found["ollama"]:
        missing.append("Ollama: https://ollama.com/download")
    if missing:
        raise SetupError("Install these first, then open a new terminal and run setup again:\n  - " + "\n  - ".join(missing))
    return found


def ollama_models(base_url: str, opener=urllib.request.urlopen) -> list[str]:
    """Installed model names, or a SetupError when the Ollama server does not answer."""
    try:
        with opener(base_url.rstrip("/") + "/api/tags", timeout=5) as r:
            return [m["name"] for m in json.load(r).get("models", [])]
    except Exception as e:
        raise SetupError(f"Ollama is installed but not running at {base_url} ({type(e).__name__}). Start it (the Ollama "
                         "app on Windows/macOS, `ollama serve` on Linux) and run setup again.") from None


def missing_models(installed: list[str], wanted: list[str] = MODELS) -> list[str]:
    have = set(installed) | {n.removesuffix(":latest") for n in installed}
    return [m for m in wanted if m not in have]


def read_env(path: Path) -> dict[str, str]:
    out = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()
    return out


def with_values(template: str, values: dict[str, str]) -> str:
    """The template with `NAME=...` lines replaced for each given name (comments and other lines kept)."""
    lines = []
    for line in template.splitlines():
        name = line.split("=", 1)[0].strip() if "=" in line and not line.lstrip().startswith("#") else None
        lines.append(f"{name}={values[name]}" if name in values else line)
    return "\n".join(lines) + "\n"


def usable_vault(value: str | None) -> bool:
    return bool(value) and value != PLACEHOLDER


def write_settings(vault: Path, rerank: bool, root: Path = ROOT) -> list[str]:
    """Create .env and dashboard/.env.local from their examples. Existing files are never overwritten. Returns notes."""
    notes = []
    vault.mkdir(parents=True, exist_ok=True)
    backend, dash = root / ".env", root / "dashboard" / ".env.local"
    if backend.exists():
        notes.append(f"kept your existing {backend.name}")
    else:
        values = {"VAULT_PATH": str(vault)}
        if not rerank:
            values["RERANK"] = "false"
        backend.write_text(with_values((root / ".env.example").read_text(encoding="utf-8"), values), encoding="utf-8")
        notes.append(f"wrote .env (research folder {vault})")
    if dash.exists():
        notes.append("kept your existing dashboard/.env.local")
    else:
        dash.write_text(with_values((root / "dashboard" / ".env.example").read_text(encoding="utf-8"),
                                    {"VAULT_PATH": str(vault)}), encoding="utf-8")
        notes.append("wrote dashboard/.env.local (same research folder)")
    return notes


def choose_vault(args, existing: dict[str, str], ask=input) -> Path:
    """Existing .env wins; then --vault; then the answer to one question (Enter = ~/ResearchDesk)."""
    if usable_vault(existing.get("VAULT_PATH")):
        return Path(existing["VAULT_PATH"])
    if args.vault:
        return Path(args.vault).expanduser().resolve()
    default = Path.home() / "ResearchDesk"
    if args.yes:
        return default
    answer = ask(f"Where should Research Desk keep your sources and reports? [{default}] ").strip().strip('"')
    return Path(answer).expanduser().resolve() if answer else default


def newest_mtime(paths: list[Path]) -> float:
    latest = 0.0
    for p in paths:
        if p.is_file():
            latest = max(latest, p.stat().st_mtime)
        elif p.is_dir():
            for f in p.rglob("*"):
                if f.is_file():
                    latest = max(latest, f.stat().st_mtime)
    return latest


def needs_npm_ci(dashboard: Path = DASHBOARD) -> bool:
    marker = dashboard / "node_modules" / ".package-lock.json"
    return not marker.exists() or marker.stat().st_mtime < (dashboard / "package-lock.json").stat().st_mtime


def needs_build(dashboard: Path = DASHBOARD) -> bool:
    build_id = dashboard / ".next" / "BUILD_ID"
    if not build_id.exists():
        return True
    sources = [dashboard / "src", dashboard / "public", dashboard / "package-lock.json", dashboard / "next.config.ts"]
    return newest_mtime(sources) > build_id.stat().st_mtime


def run(cmd: list[str], cwd: Path = ROOT, env: dict | None = None) -> None:
    say("  $ " + " ".join(Path(cmd[0]).name if i == 0 else c for i, c in enumerate(cmd)))
    if subprocess.run(cmd, cwd=cwd, env=env).returncode != 0:
        raise SetupError(f"This command failed: {' '.join(cmd)}\nSee the output above; docs/SETUP.md has a troubleshooting table.")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="One-time setup for Research Desk.")
    ap.add_argument("--yes", action="store_true", help="ask nothing; research folder ~/ResearchDesk unless --vault")
    ap.add_argument("--vault", help="folder for sources, reports and the library index")
    ap.add_argument("--no-rerank", action="store_true", help="skip the reranker (no PyTorch); sets RERANK=false")
    ap.add_argument("--skip-models", action="store_true", help="do not pull the Ollama models")
    args = ap.parse_args(argv)
    try:
        step(1, "Checking the tools")
        tools = check_tools()
        say("  uv, Node.js, npm and Ollama found")

        step(2, "Installing the Python packages (tested versions from uv.lock)")
        extras = ["--extra", "dev"] + ([] if args.no_rerank else ["--extra", "rerank"])
        run([tools["uv"], "sync", "--locked", *extras])

        existing = read_env(ROOT / ".env")
        base_url = existing.get("OLLAMA_BASE_URL") or "http://localhost:11434"
        step(3, "Ollama models")
        if args.skip_models:
            say("  skipped (--skip-models)")
        else:
            todo = missing_models(ollama_models(base_url))
            for m in todo:
                run([tools["ollama"], "pull", m])
            say("  " + ("pulled " + ", ".join(todo) if todo else "both models already installed: " + ", ".join(MODELS)))

        step(4, "Settings")
        vault = choose_vault(args, existing)
        for note in write_settings(vault, rerank=not args.no_rerank):
            say("  " + note)

        step(5, "Dashboard (tested versions from package-lock.json)")
        if needs_npm_ci():
            run([tools["npm"], "ci", "--no-audit", "--no-fund"], cwd=DASHBOARD)
        else:
            say("  packages already installed")
        if needs_build():
            run([tools["npm"], "run", "build"], cwd=DASHBOARD)
        else:
            say("  build is up to date")

        step(6, "Setup check")
        py = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        subprocess.run([str(py), str(ROOT / "scripts" / "doctor.py")], cwd=ROOT)   # ports warn until the app starts
    except SetupError as e:
        say(f"\nSetup stopped: {e}")
        return 1
    except KeyboardInterrupt:
        say("\nSetup interrupted. Run it again to continue; finished steps are skipped.")
        return 130
    say("\nReady. Start Research Desk with:\n\n  uv run scripts/start.py\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
