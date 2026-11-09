import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

RUN_SH = Path(__file__).resolve().parents[2] / ".github" / "actions" / "run-gradle-tasks" / "run.sh"

# Records one line per call, each argument in brackets; a task named "boom" fails.
STUB = """#!/usr/bin/env bash
printf 'call' >> "$STUB_LOG"
printf ' [%s]' "$@" >> "$STUB_LOG"
printf '\\n' >> "$STUB_LOG"
[ "$1" = "boom" ] && exit 3
exit 0
"""


@pytest.fixture(scope="module", autouse=True)
def need_jq_and_bash():
    missing = [tool for tool in ("jq", "bash") if shutil.which(tool) is None]
    if missing and os.environ.get("CI"):
        pytest.fail(f"{missing} must be installed on the runner: the tier would otherwise be skipped silently")
    if missing:
        pytest.skip(f"{missing} not installed")


@pytest.fixture
def project(tmp_path):
    gradlew = tmp_path / "gradlew"
    gradlew.write_text(STUB, encoding="utf-8", newline="\n")
    gradlew.chmod(gradlew.stat().st_mode | stat.S_IXUSR)
    return tmp_path


def run(project, tasks):
    env = {**os.environ, "CONDOR_TASKS": tasks, "STUB_LOG": str(project / "calls.log")}
    result = subprocess.run(
        ["bash", str(RUN_SH)], cwd=project, env=env, capture_output=True, text=True, check=False
    )
    log = project / "calls.log"
    calls = log.read_text(encoding="utf-8").splitlines() if log.exists() else []
    return result, calls


def test_one_call_per_task_in_order(project):
    result, calls = run(project, '["koverXmlReportDebug", "koverHtmlReportDebug"]')
    assert result.returncode == 0
    assert calls == ["call [koverXmlReportDebug]", "call [koverHtmlReportDebug]"]


def test_a_name_with_a_space_stays_one_argument(project):
    result, calls = run(project, '["a b"]')
    assert result.returncode == 0
    assert calls == ["call [a b]"]


@pytest.mark.parametrize("task", ["$(touch pwned)", "a;touch pwned", "`touch pwned`", "a && touch pwned"])
def test_shell_syntax_in_a_name_is_never_executed(project, task):
    result, calls = run(project, json.dumps([task]))
    assert result.returncode == 0
    assert calls == [f"call [{task}]"]
    assert not (project / "pwned").exists()


def test_the_first_failure_stops_the_run(project):
    result, calls = run(project, '["first", "boom", "never"]')
    assert result.returncode == 1
    assert calls == ["call [first]", "call [boom]"]
    assert "::error::tasks: ./gradlew boom failed" in result.stdout


@pytest.mark.parametrize(
    "tasks",
    ["[]", "not json", "", "{}", '"x"', "[1]", '[""]', '["--init-script=x"]', '["ok", "-x"]', '["a\\nb"]', '["a\\u0007"]'],
)
def test_a_bad_list_is_rejected_before_gradle_is_called(project, tasks):
    result, calls = run(project, tasks)
    assert result.returncode == 1
    assert calls == []
    assert result.stdout.startswith("::error::tasks: must be a JSON array of task names")
    assert len(result.stdout.splitlines()) == 1

