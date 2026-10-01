"""Check that the assistant can run on this machine and say how to fix anything that is missing.

  python scripts/doctor.py

Looks at: .env, the vault folder, Ollama and the models the settings need, the GPU's power limit, free memory, and the two ports.
Changes nothing. Exit code 1 if something must be fixed (warnings do not fail it).
"""
import os
import sys

from _common import ROOT

from research_assistant import doctor


def main() -> int:
    checks = doctor.run_all(ROOT, dict(os.environ))
    print(doctor.render(checks))
    return 1 if any(c.status == doctor.FAIL for c in checks) else 0


if __name__ == "__main__":
    sys.exit(main())
