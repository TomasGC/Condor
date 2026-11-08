import json

import pytest
import validate

DEFAULTS = {
    "coverage-report-tasks": '["koverXmlReportDebug", "koverHtmlReportDebug"]',
    "coverage-xml-path": "app/build/reports/kover/reportDebug.xml",
    "coverage-artifact-path": "app/build/reports/kover/",
}


def check(**overrides):
    values = {**DEFAULTS, **overrides}
    return validate.validate("kotlin-coverage", json.dumps(values))


def test_the_defaults_are_valid():
    assert check() == []


def test_a_merged_variant_is_valid():
    assert check(
        **{
            "coverage-report-tasks": '["koverXmlReportMerged", "koverHtmlReportMerged"]',
            "coverage-xml-path": "app/build/reports/kover/reportMerged.xml",
        }
    ) == []


@pytest.mark.parametrize("tasks", ['[":app:koverXmlReport"]', '["koverXmlReportDebug"]', '[":a:b:c.d_e-f"]'])
def test_task_names_in_gradle_syntax_are_valid(tasks):
    assert check(**{"coverage-report-tasks": tasks}) == []


@pytest.mark.parametrize(
    "tasks",
    [
        '["--init-script=/tmp/x.gradle"]',
        '["-q"]',
        '["koverXml", "--no-daemon"]',
        '["a b"]',
        '["a;b"]',
        '["a&&b"]',
        '["a|b"]',
        '["$(id)"]',
        '["`id`"]',
        '["a>b"]',
        '["a\\nb"]',
        '[""]',
        "[]",
        '[1]',
        '[["a"]]',
        '"koverXmlReportDebug"',
        "{}",
        "koverXmlReportDebug",
        "",
        "[",
        '["a", "b", "c", "d", "e", "f", "g", "h", "i", "j", "k"]',
        '["' + "a" * 101 + '"]',
    ],
)
def test_bad_task_lists_are_rejected_and_named(tasks):
    errors = check(**{"coverage-report-tasks": tasks})
    assert len(errors) == 1
    assert errors[0].startswith("::error::coverage-report-tasks: ")


@pytest.mark.parametrize("name", ["coverage-xml-path", "coverage-artifact-path"])
@pytest.mark.parametrize(
    "path",
    [
        "../outside",
        "a/../b",
        "a/..",
        "/etc/passwd",
        "-rf",
        "a b",
        "a;b",
        "a&b",
        "a|b",
        "$(id)",
        "`id`",
        "a*",
        "a?b",
        "a//b",
        "a\nb",
        "~/x",
        "C:\\x",
        "",
        "a" * 201,
    ],
)
def test_bad_paths_are_rejected_and_named(name, path):
    errors = check(**{name: path})
    assert len(errors) == 1
    assert errors[0].startswith(f"::error::{name}: ")


@pytest.mark.parametrize("path", ["build/reports/kover/", "app/build/reports/kover/reportDebug.xml", "a/b_c-d.e/f"])
def test_relative_paths_are_valid(path):
    assert check(**{"coverage-xml-path": path, "coverage-artifact-path": path}) == []


def test_every_bad_input_is_reported_not_only_the_first():
    errors = check(**{"coverage-report-tasks": "[]", "coverage-xml-path": "../x", "coverage-artifact-path": "/y"})
    names = [line.removeprefix("::error::").split(":")[0] for line in errors]
    assert names == ["coverage-report-tasks", "coverage-xml-path", "coverage-artifact-path"]


def test_the_error_names_the_rule_and_shows_the_value():
    (line,) = check(**{"coverage-xml-path": "../x"})
    assert line == (
        "::error::coverage-xml-path: a relative path made of letters, digits and _ . / - "
        "(no '..', not starting with '/' or '-') (got '../x')"
    )


def test_a_long_value_is_cut_and_a_newline_cannot_start_a_second_command():
    (line,) = check(**{"coverage-xml-path": "a\n::error::forged " + "x" * 300})
    assert "\n" not in line
    assert "%0A::error::forged" in line
    assert line.endswith("...')")


def test_a_percent_sign_in_a_value_is_escaped_so_it_cannot_forge_an_escape():
    (line,) = check(**{"coverage-xml-path": "a%0Ab"})
    assert "(got 'a%250Ab')" in line


def test_text_that_is_not_json_is_rejected_even_where_an_empty_list_would_be_valid(tmp_path):
    (tmp_path / "lists.json").write_text(
        json.dumps(
            {
                "title": "lists",
                "type": "object",
                "required": ["items"],
                "properties": {
                    "items": {
                        "x-rule": "a JSON array",
                        "type": "string",
                        "contentMediaType": "application/json",
                        "contentSchema": {"type": "array"},
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    assert validate.validate("lists", '{"items": "[]"}', tmp_path) == []
    (line,) = validate.validate("lists", '{"items": "not json"}', tmp_path)
    assert line == "::error::items: a JSON array (got 'not json')"


def test_other_inputs_of_the_workflow_are_ignored():
    values = {**DEFAULTS, "coverage-threshold": 80, "java-version": "21", "require-fixtures": True}
    assert validate.validate("kotlin-coverage", json.dumps(values)) == []


def test_an_input_missing_from_the_values_is_reported():
    values = {key: value for key, value in DEFAULTS.items() if key != "coverage-xml-path"}
    (line,) = validate.validate("kotlin-coverage", json.dumps(values))
    assert line.startswith("::error::coverage-xml-path: missing from the values")


@pytest.mark.parametrize("module", ["nope", "../kotlin-coverage", "Kotlin-Coverage", "", "kotlin coverage", "a/b"])
def test_an_unknown_or_unsafe_module_is_rejected(module):
    (line,) = validate.validate(module, json.dumps(DEFAULTS))
    assert line.startswith("::error::")
    assert "module" in line


@pytest.mark.parametrize("values", ["", "not json", "[]", '"x"', "null", "1"])
def test_values_that_are_not_a_json_object_are_rejected(values):
    (line,) = validate.validate("kotlin-coverage", values)
    assert line.startswith("::error::")


def test_a_new_module_is_a_spec_file_and_nothing_else(tmp_path):
    (tmp_path / "demo.json").write_text(
        json.dumps(
            {
                "title": "demo",
                "type": "object",
                "required": ["demo-count"],
                "properties": {"demo-count": {"x-rule": "a number from 1 to 5", "type": "number", "minimum": 1, "maximum": 5}},
            }
        ),
        encoding="utf-8",
    )
    assert validate.validate("demo", '{"demo-count": 3}', tmp_path) == []
    (line,) = validate.validate("demo", '{"demo-count": 9}', tmp_path)
    assert line == "::error::demo-count: a number from 1 to 5 (got '9')"
