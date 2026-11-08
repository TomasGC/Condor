import os
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests" / "fixtures" / "kotlin-project"
RUN_SH = ROOT / ".github" / "actions" / "run-gradle-tasks" / "run.sh"
REPORTS = Path("app") / "build" / "reports" / "kover"


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    """The fixture project, built once with the real Gradle wrapper through the run-gradle-tasks action."""
    missing = [tool for tool in ("java", "jq", "bash") if shutil.which(tool) is None]
    if missing and os.environ.get("CI"):
        pytest.fail(f"{missing} must be installed on the runner")
    if missing:
        pytest.skip(f"{missing} not installed")
    project = tmp_path_factory.mktemp("kotlin-project") / "project"
    shutil.copytree(FIXTURE, project, ignore=shutil.ignore_patterns("build", ".gradle", ".kotlin"))
    env = {**os.environ, "CONDOR_TASKS": '["koverXmlReportDebug", "koverXmlReportMerged", "koverHtmlReportMerged"]'}
    result = subprocess.run(
        ["bash", str(RUN_SH)], cwd=project, env=env, capture_output=True, text=True, check=False, timeout=900
    )
    assert result.returncode == 0, result.stdout[-3000:] + result.stderr[-3000:]
    return project


def line_counter(report: Path) -> tuple[int, int]:
    """(covered, missed) of the report-level LINE counter: the last LINE counter in the file."""
    counters = [c for c in ET.parse(report).getroot().findall("counter") if c.get("type") == "LINE"]
    return int(counters[-1].get("covered")), int(counters[-1].get("missed"))


def test_the_debug_report_holds_the_app_module_only(built):
    assert line_counter(built / REPORTS / "reportDebug.xml") == (2, 1)


def test_the_merged_report_holds_both_modules(built):
    assert line_counter(built / REPORTS / "reportMerged.xml") == (6, 4)


def test_the_two_reports_differ_so_a_test_can_tell_which_one_was_read(built):
    assert line_counter(built / REPORTS / "reportDebug.xml") != line_counter(built / REPORTS / "reportMerged.xml")


def test_the_html_report_is_written_next_to_the_xml(built):
    assert (built / REPORTS / "htmlMerged" / "index.html").is_file()
