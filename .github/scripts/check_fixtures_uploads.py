"""Fail when a workflow or action uploads something that could hold the private fixtures (Condor#25).

A project's private test files (real photos) are cloned into the runner's temp folder and must never leave it. The
pipelines upload test results and coverage only, from `**/build/...` paths; this check reads every workflow and action
under a folder and fails on an `actions/upload-artifact` step whose `path` names the runner's temp folder, the
fixtures variable or anything called "fixtures", so that a later edit cannot start publishing them by accident.

Usage: python check_fixtures_uploads.py FOLDER [FOLDER ...]
"""
import re
import sys
from pathlib import Path

import yaml

SUSPECT = re.compile(r"fixtures|runner\.temp|RUNNER_TEMP|FIXTURES_DIR", re.IGNORECASE)
UPLOAD = "actions/upload-artifact"


def steps_of(document):
    """Every step of a workflow (`jobs.*.steps`) or of a composite action (`runs.steps`)."""
    if not isinstance(document, dict):
        return
    for job in (document.get("jobs") or {}).values():
        yield from (job or {}).get("steps") or []
    yield from (document.get("runs") or {}).get("steps") or []


def problems(folder):
    found = []
    for file in sorted(Path(folder).rglob("*.yml")):
        for step in steps_of(yaml.safe_load(file.read_text(encoding="utf-8"))):
            if not str(step.get("uses", "")).startswith(UPLOAD):
                continue
            path = str((step.get("with") or {}).get("path", ""))
            if SUSPECT.search(path):
                found.append(f"{file}: uploads '{path}', which can hold the private fixtures")
    return found


def main(folders):
    found = [problem for folder in folders for problem in problems(folder)]
    for problem in found:
        print(f"::error::{problem}")
    if not found:
        print("No step uploads from the fixtures folder")
    return 1 if found else 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    sys.exit(main(sys.argv[1:]))
