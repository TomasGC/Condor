"""Validate the inputs of a Condor module against its spec, before anything uses them.

A module's rules live in specs/<module>.json, a JSON Schema (draft 2020-12). Each property is one workflow input
and carries `x-rule`, the sentence an error shows. An input that holds JSON (a list of Gradle tasks) is a string
with `contentMediaType: application/json` and a `contentSchema`: it is parsed, then the parsed value is checked.

Adding a module or an input is a spec change; this script does not change. Every problem is reported on
its own `::error::<input>: <rule> (got '<value>')` line, so a bad value is named before a single job starts.

The caller passes the whole `inputs` context (`${{ toJSON(inputs) }}`); inputs the spec does not name are ignored.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

SPECS_DIR = Path(__file__).resolve().parent / "specs"
MODULE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")
JSON_MEDIA_TYPE = "application/json"
SHOWN_VALUE_LENGTH = 100


def escape_annotation(text: str) -> str:
    """Escape what a workflow command cannot carry on one line."""
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def shown(value: Any) -> str:
    text = value if isinstance(value, str) else json.dumps(value)
    return text if len(text) <= SHOWN_VALUE_LENGTH else text[:SHOWN_VALUE_LENGTH] + "..."


def error_line(name: str, rule: str, value: Any) -> str:
    return escape_annotation(f"::error::{name}: {rule} (got '{shown(value)}')")


def load_spec(module: str, specs_dir: Path) -> dict[str, Any]:
    if not MODULE_PATTERN.match(module):
        raise ValueError(f"module name must be lowercase letters, digits and '-' (got '{shown(module)}')")
    path = specs_dir / f"{module}.json"
    if not path.is_file():
        known = ", ".join(sorted(p.stem for p in specs_dir.glob("*.json")))
        raise ValueError(f"unknown module '{module}'; known modules: {known}")
    return json.loads(path.read_text(encoding="utf-8"))


def check_property(name: str, value: Any, spec: dict[str, Any]) -> list[str]:
    """Errors of one input; the spec's own x-rule is the message."""
    rule = spec.get("x-rule", "does not match its spec")
    schema, instance = spec, value
    if spec.get("contentMediaType") == JSON_MEDIA_TYPE and isinstance(value, str):
        try:
            instance = json.loads(value)
        except json.JSONDecodeError:
            return [error_line(name, rule, value)]
        schema = spec["contentSchema"]
    if next(Draft202012Validator(schema).iter_errors(instance), None) is None:
        return []
    return [error_line(name, rule, value)]


def validate(module: str, values_json: str, specs_dir: Path = SPECS_DIR) -> list[str]:
    """Return one `::error::` line per invalid input; an empty list means the inputs are valid."""
    try:
        spec = load_spec(module, specs_dir)
        values = json.loads(values_json)
    except (ValueError, OSError) as error:
        return [escape_annotation(f"::error::{error}")]
    if not isinstance(values, dict):
        return [escape_annotation("::error::values must be a JSON object (pass ${{ toJSON(inputs) }})")]

    errors = []
    for name in spec.get("required", []):
        if name not in values:
            errors.append(escape_annotation(f"::error::{name}: missing from the values, so it cannot be checked"))
    for name, property_spec in spec.get("properties", {}).items():
        if name in values:
            errors.extend(check_property(name, values[name], property_spec))
    return errors


def main() -> int:
    errors = validate(os.environ.get("CONDOR_MODULE", ""), os.environ.get("CONDOR_VALUES", ""))
    for line in errors:
        print(line)
    if errors:
        print(f"{len(errors)} input(s) rejected before anything ran", file=sys.stderr)
        return 1
    print("Inputs are valid")
    return 0


if __name__ == "__main__":
    sys.exit(main())
