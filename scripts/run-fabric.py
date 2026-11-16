"""Run the Fabric CLI directly from a development checkout.

Installed releases use their global launcher for normal operations. This helper is the
source-versioned installer entry point for first installation, reviewed cross-version
bootstrap and launcher delegation. It does not itself create state without an invoked
state-changing command.
"""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_agent_fabric.__main__ import main


if __name__ == "__main__":
    main()
