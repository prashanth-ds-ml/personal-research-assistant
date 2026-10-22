"""Setup check: is everything the assistant needs in place? Each check returns a result with a plain-language fix.

Used by ``scripts/doctor.py`` (and ``make doctor``). Pure functions with the outside world passed in (HTTP client, paths),
so they are tested offline. Nothing here changes anything: it only looks and says what to do.
"""

import importlib.util
import os
import shutil
import socket
import subprocess
from dataclasses import dataclass
from pathlib import Path

import httpx

OK, WARN, FAIL = "ok", "warn", "fail"


@dataclass
class Check:
    name: str
    status: str
    detail: str
    fix: str = ""


def required_models(env: dict) -> dict[str, str]:
    """Model name -> what it is used for, from the settings the app reads (env first, then the defaults)."""
    local = env.get("LOCAL_LLM") or "qwen3.5:4b"
    embed = (env.get("EMBEDDING_MODEL") or "ollama:qwen3-embedding:0.6b").removeprefix("ollama:")
    needs = {local: "planning and extraction"}
    needs.setdefault(env.get("PLANNER_MODEL") or local, "planning")
    needs.setdefault(env.get("EXTRACTOR_MODEL") or local, "evidence extraction")
    needs.setdefault(env.get("WRITER_MODEL") or local, "writing the report")
    needs[embed] = "search embeddings"
    return needs


def check_ollama(base_url: str, env: dict, http: httpx.Client | None = None) -> list[Check]:
    http = http or httpx.Client(timeout=5)
    try:
        tags = http.get(f"{base_url.rstrip('/')}/api/tags").json()
    except Exception as e:
        return [Check("Ollama", FAIL, f"not reachable at {base_url} ({type(e).__name__})",
                      "Install Ollama from https://ollama.com and start it, then run this check again")]
    have = {m.get("name", "") for m in tags.get("models", [])}
    have |= {n.removesuffix(":latest") for n in have}
    out = [Check("Ollama", OK, f"running at {base_url}")]
    for model, use in required_models(env).items():
        if model in have or f"{model}:latest" in have:
            out.append(Check(f"Model {model}", OK, f"installed ({use})"))
        else:
            out.append(Check(f"Model {model}", FAIL, f"not installed ({use})", f"ollama pull {model}"))
    return out


def check_vault(vault_path: str) -> Check:
    if not vault_path or "/absolute/path" in vault_path:
        return Check("Vault folder", FAIL, "VAULT_PATH is not set (or still the placeholder from .env.example)",
                     "Set VAULT_PATH in .env to an empty folder you own, for example ~/ResearchVault")
    p = Path(vault_path).expanduser()
    if not p.exists():
        return Check("Vault folder", WARN, f"{p} does not exist yet", f"Create it: mkdir {p}  (the app also creates it on first run)")
    if not os.access(p, os.W_OK):
        return Check("Vault folder", FAIL, f"{p} is not writable", "Pick a folder you can write to, or fix its permissions")
    return Check("Vault folder", OK, f"{p} (writable)")


def check_env_file(root: Path) -> Check:
    if (root / ".env").exists():
        return Check(".env", OK, "present")
    return Check(".env", FAIL, "missing", "cp .env.example .env  and set VAULT_PATH")


def port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def check_port(port: int, what: str, in_use=port_in_use) -> Check:
    if in_use(port):
        return Check(f"Port {port} ({what})", OK, "something is listening (fine if it is this app)")
    return Check(f"Port {port} ({what})", WARN, "nothing is listening yet", "Start it as the README shows (normal before the first start)")


def check_memory(free_gb: float | None, needed_gb: float = 12.0) -> Check:
    if free_gb is None:
        return Check("Free memory", WARN, "could not read free memory", "Install psutil for this check: pip install psutil")
    if free_gb < needed_gb:
        return Check("Free memory", WARN, f"{free_gb:.1f} GB free (a deep research run uses about 11-12 GB: model, reranker, PDF conversion)",
                     "Close browsers and other large programs before a long run")
    return Check("Free memory", OK, f"{free_gb:.1f} GB free")


def check_reranker(env: dict, has=None) -> Check:
    """RERANK is on by default and needs torch + transformers, which a plain install does not bring."""
    if str(env.get("RERANK", "true")).strip().lower() in ("false", "0", "no"):
        return Check("Reranker", OK, "off (RERANK=false)")
    has = has or (lambda m: importlib.util.find_spec(m) is not None)
    missing = [m for m in ("torch", "transformers") if not has(m)]
    if missing:
        return Check("Reranker", FAIL, f"RERANK is on but {', '.join(missing)} is not installed",
                     'uv sync --extra rerank  (or set RERANK=false in .env)')
    return Check("Reranker", OK, "torch and transformers installed (the model downloads ~2 GB on first use)")


def free_memory_gb() -> float | None:
    try:
        import psutil
        return psutil.virtual_memory().available / 1e9
    except Exception:
        return None


def check_gpu(read=None) -> Check:
    """On NVIDIA machines: warn when the GPU's power limit is far below its default (a power cap made runs 5-10x slower)."""
    row = (read or _nvidia_smi)()
    if row is None:
        return Check("GPU", WARN, "no NVIDIA GPU found (or nvidia-smi is missing): models will run on the CPU and be slow",
                     "Runs still work; expect long waits")
    name, limit, default = row
    if limit is None:
        return Check("GPU", OK, f"{name} (power limit not reported)")
    if default and limit < 0.4 * default:
        return Check("GPU", WARN, f"{name}: power limit {limit:.0f} W against a default of {default:.0f} W",
                     "Check the charger and the laptop's performance mode; a capped GPU makes runs 5-10x slower")
    return Check("GPU", OK, f"{name} (power limit {limit:.0f} W)")


def _number(text: str) -> float | None:
    try:
        return float(text.strip().split()[0])
    except (ValueError, IndexError):
        return None


def _nvidia_smi():
    """(name, current power limit or None, default limit or None), or None when there is no NVIDIA GPU. Some laptop GPUs
    report the limit as [N/A] in the short query; then the long listing's "Current Power Limit" lines are used."""
    exe = shutil.which("nvidia-smi")
    if not exe:
        return None
    try:
        out = subprocess.run([exe, "--query-gpu=name,power.limit,power.default_limit", "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=10).stdout.strip().splitlines()[0]
        name, limit, default = [x.strip() for x in out.split(",")]
        limit, default = _number(limit), _number(default)
        if limit is None:
            long = subprocess.run([exe, "-q", "-d", "POWER"], capture_output=True, text=True, timeout=10).stdout
            values = [_number(line.split(":", 1)[1]) for line in long.splitlines()
                      if "Current Power Limit" in line and ":" in line]
            values = [v for v in values if v is not None]
            limit = min(values) if values else None
        return name, limit, default
    except Exception:
        return None


def run_all(root: Path, env: dict, http: httpx.Client | None = None) -> list[Check]:
    base = (env.get("OLLAMA_BASE_URL") or "http://localhost:11434")
    return [check_env_file(root), check_vault(env.get("VAULT_PATH", "")), *check_ollama(base, env, http),
            check_reranker(env), check_gpu(), check_memory(free_memory_gb()), check_port(2025, "backend"), check_port(3001, "dashboard")]


def render(checks: list[Check]) -> str:
    mark = {OK: "[ok]  ", WARN: "[warn]", FAIL: "[FAIL]"}
    lines = []
    for c in checks:
        lines.append(f"{mark[c.status]} {c.name}: {c.detail}")
        if c.fix and c.status != OK:
            lines.append(f"        -> {c.fix}")
    failed = sum(c.status == FAIL for c in checks)
    warned = sum(c.status == WARN for c in checks)
    lines.append("")
    lines.append("Everything needed is in place." if not failed and not warned
                 else f"{failed} problem(s) to fix, {warned} warning(s)." if failed else f"Ready, with {warned} warning(s).")
    return "\n".join(lines)
