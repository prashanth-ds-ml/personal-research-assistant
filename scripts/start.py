"""Start Research Desk: the research backend (langgraph dev) and the dashboard, together. Ctrl+C stops both.

  uv run scripts/start.py                         backend on 2025, dashboard on 3001, opens the browser
  uv run scripts/start.py --no-browser
  uv run scripts/start.py --backend-port 2099 --dashboard-port 3099

Logs: logs/backend.log and logs/dashboard.log. Run scripts/setup.py once before the first start.
Standard library only.
"""
import argparse
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DASHBOARD = ROOT / "dashboard"
LOGS = ROOT / "logs"
WINDOWS = os.name == "nt"


def venv_path(root: Path, name: str) -> Path:
    return root / ".venv" / ("Scripts" if WINDOWS else "bin") / (name + (".exe" if WINDOWS else ""))


def preflight(root: Path = ROOT) -> list[str]:
    """What is missing before a start, each with its fix. Empty = ready."""
    problems = []
    if not (root / ".env").exists() or not (root / "dashboard" / ".env.local").exists():
        problems.append("settings are missing: run  uv run scripts/setup.py")
    if not venv_path(root, "langgraph").exists():
        problems.append("the Python packages are not installed: run  uv run scripts/setup.py")
    if not (root / "dashboard" / ".next" / "BUILD_ID").exists():
        problems.append("the dashboard is not built: run  uv run scripts/setup.py")
    return problems


def port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def http_ok(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=3) as r:
            return r.status == 200
    except Exception:
        return False


def commands(root: Path, backend_port: int, dashboard_port: int, base_env: dict[str, str]) -> dict[str, dict]:
    """How to start each server: command, working folder and environment."""
    backend_env = {**base_env, "PYTHONUTF8": "1"}                       # Windows consoles choke on non-ASCII log lines
    dashboard_env = {**base_env,
                     "LANGGRAPH_API_URL": f"http://127.0.0.1:{backend_port}",
                     "PYTHON_BIN": str(venv_path(root, "python")),       # the dashboard's library actions use this Python
                     "RESEARCH_ROOT": str(root)}
    next_bin = root / "dashboard" / "node_modules" / "next" / "dist" / "bin" / "next"
    return {
        "backend": {"cmd": [str(venv_path(root, "langgraph")), "dev", "--no-browser", "--no-reload",
                            "--port", str(backend_port)],
                    "cwd": root, "env": backend_env, "url": f"http://127.0.0.1:{backend_port}/ok"},
        "dashboard": {"cmd": ["node", str(next_bin), "start", "-H", "127.0.0.1", "-p", str(dashboard_port)],
                      "cwd": root / "dashboard", "env": dashboard_env, "url": f"http://127.0.0.1:{dashboard_port}/"},
    }


def tail(path: Path, n: int = 15) -> str:
    try:
        return "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[-n:])
    except OSError:
        return "(no log)"


def launch(spec: dict, log: Path) -> subprocess.Popen:
    log.parent.mkdir(parents=True, exist_ok=True)
    out = open(log, "w", encoding="utf-8")
    kw = {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if WINDOWS else {"start_new_session": True}
    return subprocess.Popen(spec["cmd"], cwd=spec["cwd"], env=spec["env"], stdout=out, stderr=subprocess.STDOUT, **kw)


def stop(proc: subprocess.Popen) -> None:
    """Stop a server and everything it started."""
    if proc.poll() is not None:
        return
    if WINDOWS:
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True)
    else:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
            proc.wait(timeout=10)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        pass


def _interrupt(signum, frame):
    raise KeyboardInterrupt


def main(argv: list[str] | None = None) -> int:
    # Closing the terminal (Windows: SIGBREAK) or a plain kill (SIGTERM) stops both servers like Ctrl+C does.
    for name in ("SIGTERM", "SIGBREAK"):
        if hasattr(signal, name):
            signal.signal(getattr(signal, name), _interrupt)
    ap = argparse.ArgumentParser(description="Start Research Desk (backend + dashboard).")
    ap.add_argument("--backend-port", type=int, default=2025)
    ap.add_argument("--dashboard-port", type=int, default=3001)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--timeout", type=int, default=180, help="seconds to wait for both to answer")
    args = ap.parse_args(argv)

    problems = preflight()
    if problems:
        print("Not ready yet:\n  - " + "\n  - ".join(problems))
        return 1
    for port, what, flag in ((args.backend_port, "backend", "--backend-port"),
                             (args.dashboard_port, "dashboard", "--dashboard-port")):
        if port_in_use(port):
            print(f"Port {port} ({what}) is already in use. If Research Desk is already running, open "
                  f"http://127.0.0.1:{args.dashboard_port}; otherwise stop the other program or pick another port "
                  f"with {flag}.")
            return 1

    specs = commands(ROOT, args.backend_port, args.dashboard_port, dict(os.environ))
    logs = {name: LOGS / f"{name}.log" for name in specs}
    procs: dict[str, subprocess.Popen] = {}
    try:
        for name, spec in specs.items():
            procs[name] = launch(spec, logs[name])
        print(f"Starting the backend (port {args.backend_port}) and the dashboard (port {args.dashboard_port})...",
              flush=True)
        deadline = time.time() + args.timeout
        ready = set()
        while ready != set(specs):
            for name, proc in procs.items():
                if proc.poll() is not None:
                    print(f"\nThe {name} stopped while starting. Last lines of {logs[name]}:\n{tail(logs[name])}")
                    return 1
                if name not in ready and http_ok(specs[name]["url"]):
                    ready.add(name)
                    print(f"  {name} is up", flush=True)
            if time.time() > deadline:
                waiting = ", ".join(sorted(set(specs) - ready))
                print(f"\nStill waiting for: {waiting} after {args.timeout} s. See {LOGS}.")
                return 1
            time.sleep(1)

        url = f"http://127.0.0.1:{args.dashboard_port}"
        print(f"\nResearch Desk is running: {url}\nLogs: {LOGS}\nPress Ctrl+C to stop.", flush=True)
        if not args.no_browser:
            webbrowser.open(url)
        while True:
            for name, proc in procs.items():
                if proc.poll() is not None:
                    print(f"\nThe {name} stopped. Last lines of {logs[name]}:\n{tail(logs[name])}")
                    return 1
            time.sleep(2)
    except KeyboardInterrupt:
        print("\nStopping...", flush=True)
        return 0
    finally:
        for proc in procs.values():
            stop(proc)
        if procs:
            print("Stopped.", flush=True)


if __name__ == "__main__":
    sys.exit(main())
