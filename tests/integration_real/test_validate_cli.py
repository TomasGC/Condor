import json
import os
import subprocess
import sys
from pathlib import Path

import validate

SCRIPT = Path(validate.__file__)
VALID = {
    "coverage-report-tasks": '["koverXmlReportMerged"]',
    "coverage-xml-path": "app/build/reports/kover/reportMerged.xml",
    "coverage-artifact-path": "app/build/reports/kover/",
}


def run(module, values):
    env = {**os.environ, "CONDOR_MODULE": module, "CONDOR_VALUES": values}
    return subprocess.run([sys.executable, str(SCRIPT)], env=env, capture_output=True, text=True, check=False)


def test_valid_inputs_exit_zero():
    result = run("kotlin-coverage", json.dumps(VALID))
    assert result.returncode == 0
    assert "Inputs are valid" in result.stdout


def test_a_rejected_input_exits_one_and_prints_the_workflow_command_on_stdout():
    values = {**VALID, "coverage-report-tasks": '["--init-script=/tmp/x.gradle"]'}
    result = run("kotlin-coverage", json.dumps(values))
    assert result.returncode == 1
    assert result.stdout.startswith("::error::coverage-report-tasks: ")
    assert "rejected before anything ran" in result.stderr


def test_a_value_with_shell_syntax_is_data_not_code(tmp_path):
    marker = tmp_path / "executed"
    values = {**VALID, "coverage-xml-path": f"$(touch {marker})"}
    result = run("kotlin-coverage", json.dumps(values))
    assert result.returncode == 1
    assert not marker.exists()


def github_output(tmp_path, module, values):
    output = tmp_path / "github_output"
    env = {**os.environ, "CONDOR_MODULE": module, "CONDOR_VALUES": values, "GITHUB_OUTPUT": str(output)}
    subprocess.run([sys.executable, str(SCRIPT)], env=env, capture_output=True, text=True, check=False)
    return output.read_text(encoding="utf-8") if output.exists() else ""


def test_the_number_of_rejected_inputs_is_a_step_output(tmp_path):
    bad = {**VALID, "coverage-xml-path": "../x", "coverage-artifact-path": "/y"}
    assert github_output(tmp_path, "kotlin-coverage", json.dumps(bad)).splitlines() == ["rejected=2"]


def test_valid_inputs_report_zero_rejected(tmp_path):
    assert github_output(tmp_path, "kotlin-coverage", json.dumps(VALID)).splitlines() == ["rejected=0"]


def test_no_environment_is_an_error_not_a_crash():
    env = {key: value for key, value in os.environ.items() if not key.startswith("CONDOR_")}
    result = subprocess.run([sys.executable, str(SCRIPT)], env=env, capture_output=True, text=True, check=False)
    assert result.returncode == 1
    assert result.stdout.startswith("::error::")
