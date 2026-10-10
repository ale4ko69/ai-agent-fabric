"""Run the Fabric CLI directly from a development checkout.

Installed releases use their own Bash launcher. This helper is only the portable
bootstrap path before the first release exists and deliberately creates no state.
"""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_agent_fabric.__main__ import main


if __name__ == "__main__":
    main()
