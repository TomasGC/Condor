import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".github" / "scripts"))
sys.path.insert(0, str(ROOT / ".github" / "actions" / "validate-inputs"))
sys.path.insert(0, str(ROOT / ".github" / "actions" / "check-coverage"))
