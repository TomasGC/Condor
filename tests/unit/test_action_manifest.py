from pathlib import Path

import pytest
import yaml

ACTIONS_DIR = Path(__file__).resolve().parents[2] / ".github" / "actions"
MANIFESTS = sorted(ACTIONS_DIR.glob("*/action.yml"))


def descriptions(manifest: dict) -> list[tuple[str, str]]:
    found = [("action", manifest.get("description", ""))]
    for section in ("inputs", "outputs"):
        for name, entry in (manifest.get(section) or {}).items():
            found.append((f"{section}.{name}", entry.get("description", "")))
    return found


def test_there_are_manifests_to_check():
    assert MANIFESTS


@pytest.mark.parametrize("path", MANIFESTS, ids=lambda path: path.parent.name)
def test_no_description_holds_an_expression(path):
    """GitHub evaluates `${{ }}` in a description at load time, where `inputs` is not a context: the action
    then fails to load (seen on Condor's validate-inputs run, 'Unrecognized named-value: inputs')."""
    manifest = yaml.safe_load(path.read_text(encoding="utf-8"))
    offenders = [where for where, text in descriptions(manifest) if "${{" in str(text)]
    assert offenders == []
