import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

WARM_SH = Path(__file__).resolve().parents[2] / ".github" / "actions" / "warm-gradle-wrapper" / "warm.sh"

# Counts its calls in $STUB_COUNT and fails the first $STUB_FAIL_FIRST of them.
GRADLEW = """#!/usr/bin/env bash
n=$(( $(cat "$STUB_COUNT" 2>/dev/null || echo 0) + 1 ))
echo "$n" > "$STUB_COUNT"
echo "gradlew $* (call $n)"
[ "$n" -le "${STUB_FAIL_FIRST:-0}" ] && exit 7
exit 0
"""

# Replaces sleep: records its argument and returns at once.
SLEEP = """#!/usr/bin/env bash
echo "$1" >> "$STUB_SLEEPS"
"""


@pytest.fixture(scope="module", autouse=True)
def need_bash():
    if shutil.which("bash") is None:
        if os.environ.get("CI"):
            pytest.fail("bash must be installed on the runner: the tier would otherwise be skipped silently")
        pytest.skip("bash not installed")


def executable(path, text):
    path.write_text(text, encoding="utf-8", newline="\n")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


@pytest.fixture
def project(tmp_path):
    executable(tmp_path / "gradlew", GRADLEW)
    (tmp_path / "bin").mkdir()
    executable(tmp_path / "bin" / "sleep", SLEEP)
    return tmp_path


def run(project, attempts="4", backoff="10", fail_first=0):
    env = {
        **os.environ,
        "PATH": f"{project / 'bin'}{os.pathsep}{os.environ['PATH']}",
        "CONDOR_ATTEMPTS": attempts,
        "CONDOR_BACKOFF_SECONDS": backoff,
        "STUB_COUNT": str(project / "count"),
        "STUB_SLEEPS": str(project / "sleeps"),
        "STUB_FAIL_FIRST": str(fail_first),
    }
    result = subprocess.run(
        ["bash", str(WARM_SH)], cwd=project, env=env, capture_output=True, text=True, check=False
    )
    count = int((project / "count").read_text()) if (project / "count").exists() else 0
    sleeps = [int(s) for s in (project / "sleeps").read_text().split()] if (project / "sleeps").exists() else []
    return result, count, sleeps


def test_success_on_the_first_attempt_calls_once_and_never_sleeps(project):
    result, count, sleeps = run(project)
    assert (result.returncode, count, sleeps) == (0, 1, [])
    assert "gradlew --version" in result.stdout


def test_success_after_two_failures_retries_twice_and_names_each_attempt(project):
    result, count, sleeps = run(project, fail_first=2)
    assert (result.returncode, count, len(sleeps)) == (0, 3, 2)
    assert "::warning::./gradlew --version failed (attempt 1 of 4); retrying in" in result.stdout
    assert "::warning::./gradlew --version failed (attempt 2 of 4); retrying in" in result.stdout
    assert "::error::" not in result.stdout


def test_failure_after_the_last_attempt_calls_exactly_attempts_times(project):
    result, count, sleeps = run(project, attempts="3", fail_first=99)
    assert (result.returncode, count, len(sleeps)) == (1, 3, 2)
    assert "::error::./gradlew --version failed after 3 attempts" in result.stdout
    assert "gradlew --version (call 3)" in result.stdout  # Gradle's own output is above the error


def test_the_wait_doubles_and_carries_at_most_a_quarter_of_jitter(project):
    _, _, sleeps = run(project, attempts="4", backoff="8", fail_first=99)
    assert len(sleeps) == 3
    for pause, base in zip(sleeps, (8, 16, 32)):
        assert base <= pause <= base + base // 4


def test_a_backoff_of_zero_is_valid(project):
    result, count, sleeps = run(project, attempts="3", backoff="0", fail_first=1)
    assert (result.returncode, count, sleeps) == (0, 2, [0])


def test_one_attempt_never_retries(project):
    result, count, sleeps = run(project, attempts="1", fail_first=99)
    assert (result.returncode, count, sleeps) == (1, 1, [])


@pytest.mark.parametrize("attempts", ["0", "11", "abc", "", "-1", "2.5", "1;touch x", "3\n::error::forged"])
def test_a_bad_attempts_is_refused_before_any_call(project, attempts):
    result, count, _ = run(project, attempts=attempts)
    assert result.returncode == 1
    assert count == 0
    assert "::error::attempts: must be an integer from 1 to 10" in result.stdout
    assert "forged" not in result.stdout


@pytest.mark.parametrize("backoff", ["121", "-1", "x", "", "1.5", "5\n::error::forged"])
def test_a_bad_backoff_is_refused_before_any_call(project, backoff):
    result, count, _ = run(project, backoff=backoff)
    assert result.returncode == 1
    assert count == 0
    assert "::error::backoff-seconds: must be an integer from 0 to 120" in result.stdout
    assert "forged" not in result.stdout


def test_a_missing_wrapper_is_refused_without_retrying(project):
    (project / "gradlew").unlink()
    result, count, sleeps = run(project)
    assert (result.returncode, count, sleeps) == (1, 0, [])
    assert "::error::no ./gradlew in" in result.stdout
