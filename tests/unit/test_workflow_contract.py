"""The public contract of the Kotlin workflows: frozen defaults, forwarded inputs, no expression in a shell."""
import json
from pathlib import Path

import pytest
import validate
import yaml

WORKFLOWS = Path(__file__).resolve().parents[2] / ".github" / "workflows"
SPECS = Path(validate.__file__).parent / "specs"

# Today's values. A default is part of the contract: changing one changes the behaviour of every caller that
# does not set it (Anglerfish, Otter, Raven), so this test is the thing to edit only with a major version.
FROZEN_DEFAULTS = {
    "coverage-report-tasks": '["koverXmlReportDebug", "koverHtmlReportDebug"]',
    "coverage-xml-path": "app/build/reports/kover/reportDebug.xml",
    "coverage-artifact-path": "app/build/reports/kover/",
}

# `run: ${{ inputs.pre-test-command }}` is a feature: the caller hands Condor a shell command to run.
SHELL_EXPRESSION_EXCEPTIONS = {("coverage", "Pre-coverage setup")}


def load(name):
    return yaml.safe_load((WORKFLOWS / name).read_text(encoding="utf-8"))


def inputs_of(name):
    return load(name)[True]["workflow_call"]["inputs"]  # PyYAML reads the key `on` as True


@pytest.mark.parametrize("workflow", ["kotlin-coverage.yml", "kotlin-push-ci.yml"])
@pytest.mark.parametrize(("name", "default"), FROZEN_DEFAULTS.items())
def test_the_defaults_are_todays_values(workflow, name, default):
    assert inputs_of(workflow)[name]["default"] == default


@pytest.mark.parametrize("workflow", ["kotlin-coverage.yml", "kotlin-push-ci.yml"])
def test_the_defaults_pass_the_spec(workflow):
    values = {name: entry.get("default") for name, entry in inputs_of(workflow).items()}
    assert validate.validate("kotlin-coverage", json.dumps(values), SPECS) == []


def test_push_ci_forwards_the_three_inputs_to_coverage():
    with_block = load("kotlin-push-ci.yml")["jobs"]["coverage"]["with"]
    for name in FROZEN_DEFAULTS:
        assert with_block[name] == "${{ inputs." + name + " }}"


def validator_steps():
    early = load("kotlin-push-ci.yml")["jobs"]["validate-environments"]["steps"]
    late = load("kotlin-coverage.yml")["jobs"]["coverage"]["steps"]
    return {"push-ci, first job": early, "coverage job": late}


@pytest.mark.parametrize("where", ["push-ci, first job", "coverage job"])
def test_each_workflow_validates_the_coverage_inputs_with_the_whole_inputs_context(where):
    steps = [s for s in validator_steps()[where] if "validate-inputs" in s.get("uses", "")]
    assert len(steps) == 1
    assert steps[0]["with"] == {"module": "kotlin-coverage", "values": "${{ toJSON(inputs) }}"}


def test_the_coverage_job_validates_before_anything_else():
    assert "validate-inputs" in load("kotlin-coverage.yml")["jobs"]["coverage"]["steps"][0]["uses"]


def test_the_coverage_job_reads_the_repository_and_nothing_more():
    assert load("kotlin-coverage.yml")["jobs"]["coverage"]["permissions"] == {"contents": "read"}


def test_no_expression_sits_inside_a_shell_step_of_the_coverage_workflow():
    steps = load("kotlin-coverage.yml")["jobs"]["coverage"]["steps"]
    offenders = [
        step.get("name", step.get("uses"))
        for step in steps
        if "${{" in str(step.get("run", "")) and ("coverage", step.get("name")) not in SHELL_EXPRESSION_EXCEPTIONS
    ]
    assert offenders == []
