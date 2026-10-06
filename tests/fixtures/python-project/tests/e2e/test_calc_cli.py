"""E2E tier: the script run as a process."""

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "src" / "calc.py"


def test_cli_prints_the_sum():
    result = subprocess.run(
        [sys.executable, str(SCRIPT), "2", "3"], capture_output=True, text=True, check=True, timeout=30
    )
    assert result.stdout == "5\n"
