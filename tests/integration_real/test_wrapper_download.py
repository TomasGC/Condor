import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "kotlin-project"
WARM_SH = ROOT / ".github" / "actions" / "warm-gradle-wrapper" / "warm.sh"


@pytest.fixture(scope="module")
def unreachable(tmp_path_factory):
    """The fixture's real wrapper, pointed at a port nothing listens on."""
    missing = [tool for tool in ("java", "bash") if shutil.which(tool) is None]
    if missing and os.environ.get("CI"):
        pytest.fail(f"{missing} must be installed on the runner")
    if missing:
        pytest.skip(f"{missing} not installed")
    project = tmp_path_factory.mktemp("wrapper") / "project"
    (project / "gradle" / "wrapper").mkdir(parents=True)
    shutil.copy(FIXTURE / "gradlew", project / "gradlew")
    shutil.copy(FIXTURE / "gradle" / "wrapper" / "gradle-wrapper.jar", project / "gradle" / "wrapper")
    (project / "gradle" / "wrapper" / "gradle-wrapper.properties").write_text(
        "distributionBase=GRADLE_USER_HOME\n"
        "distributionPath=wrapper/dists\n"
        "distributionUrl=http\\://127.0.0.1:9/gradle-9.9.0-bin.zip\n"
        "networkTimeout=2000\n"
        "zipStoreBase=GRADLE_USER_HOME\n"
        "zipStorePath=wrapper/dists\n",
        encoding="utf-8",
        newline="\n",
    )
    env = {
        **os.environ,
        "CONDOR_ATTEMPTS": "2",
        "CONDOR_BACKOFF_SECONDS": "0",
        "GRADLE_USER_HOME": str(project / "gradle-home"),
    }
    return subprocess.run(
        ["bash", str(WARM_SH)], cwd=project, env=env, capture_output=True, text=True, check=False, timeout=300
    )


def test_a_download_that_never_works_fails_after_exactly_the_attempts(unreachable):
    assert unreachable.returncode == 1
    assert "::error::./gradlew --version failed after 2 attempts" in unreachable.stdout


def test_the_first_failure_is_a_warning_naming_the_attempt(unreachable):
    assert unreachable.stdout.count("::warning::./gradlew --version failed (attempt 1 of 2)") == 1
    assert "attempt 2 of 2" not in unreachable.stdout


def test_gradles_own_error_is_not_hidden(unreachable):
    assert "127.0.0.1:9" in unreachable.stdout + unreachable.stderr
