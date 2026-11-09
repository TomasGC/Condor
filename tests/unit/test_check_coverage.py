import pytest

import check_coverage


def report(path, covered, missed, nested=((1, 99),)):
    """A Kover-shaped report: nested counters first, the report's own LINE counter last."""
    inner = "".join(f'<counter type="LINE" missed="{m}" covered="{c}"/>' for c, m in nested)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f'<report name="x"><package name="p">{inner}</package>'
        f'<counter type="BRANCH" missed="50" covered="50"/>'
        f'<counter type="LINE" missed="{missed}" covered="{covered}"/></report>',
        encoding="utf-8",
    )
    return str(path)


def test_percentage_is_the_report_level_line_counter(tmp_path, capsys):
    path = report(tmp_path / "r.xml", covered=2, missed=1)
    assert check_coverage.check(path, 60) == 0
    assert "Coverage: 66% (2/3 lines)" in capsys.readouterr().out


def test_a_nested_counter_is_not_the_total(tmp_path, capsys):
    path = report(tmp_path / "r.xml", covered=6, missed=4, nested=((1, 99), (5, 5)))
    assert check_coverage.check(path, 0) == 0
    assert "Coverage: 60% (6/10 lines)" in capsys.readouterr().out


def test_only_the_report_elements_own_counter_counts_wherever_nested_ones_sit(tmp_path, capsys):
    path = tmp_path / "r.xml"
    path.write_text(
        '<report><counter type="LINE" missed="4" covered="6"/>'
        '<package><counter type="LINE" missed="0" covered="1"/></package></report>',
        encoding="utf-8",
    )
    assert check_coverage.check(str(path), 0) == 0
    assert "Coverage: 60% (6/10 lines)" in capsys.readouterr().out


@pytest.mark.parametrize(("threshold", "expected"), [(66, 0), (66.0, 0), (67, 1), (65.5, 0), (66.5, 1)])
def test_threshold_boundary_is_strictly_below(tmp_path, threshold, expected):
    path = report(tmp_path / "r.xml", covered=2, missed=1)
    assert check_coverage.check(path, threshold) == expected


def test_below_threshold_prints_an_error_with_both_numbers(tmp_path, capsys):
    path = report(tmp_path / "r.xml", covered=2, missed=1)
    assert check_coverage.check(path, 80) == 1
    # `%` travels as %25 in a workflow command; GitHub shows it back as `%`
    assert "::error::Coverage 66%25 below threshold 80%25" in capsys.readouterr().out


def test_success_message(tmp_path, capsys):
    path = report(tmp_path / "r.xml", covered=2, missed=1)
    check_coverage.check(path, 60)
    assert "SUCCESS: Coverage 66% >= 60%" in capsys.readouterr().out


def test_percentage_is_appended_to_the_output_file_and_nothing_else(tmp_path):
    out = tmp_path / "out.txt"
    out.write_text("earlier=1\n", encoding="utf-8")
    check_coverage.check(report(tmp_path / "r.xml", 2, 1), 60, str(out))
    assert out.read_text(encoding="utf-8") == "earlier=1\npercentage=66\n"


def test_percentage_is_written_even_when_the_threshold_fails(tmp_path):
    out = tmp_path / "out.txt"
    assert check_coverage.check(report(tmp_path / "r.xml", 2, 1), 90, str(out)) == 1
    assert out.read_text(encoding="utf-8") == "percentage=66\n"


def test_missing_report_names_the_path_the_hint_and_what_was_found(tmp_path, capsys):
    folder = tmp_path / "app" / "build" / "reports" / "kover"
    report(folder / "reportMerged.xml", 1, 1)
    wanted = str(folder / "reportDebug.xml")
    assert check_coverage.check(wanted, 80) == 1
    out = capsys.readouterr().out
    assert out.startswith("::error::coverage-xml-path: no report at ")
    assert wanted in out
    assert "report<Variant>.xml" in out
    assert str(folder / "reportMerged.xml") in out
    assert len(out.splitlines()) == 1


def test_missing_report_in_a_folder_with_no_xml(tmp_path, capsys):
    (tmp_path / "kover").mkdir()
    assert check_coverage.check(str(tmp_path / "kover" / "r.xml"), 80) == 1
    assert "no .xml file under" in capsys.readouterr().out


def test_missing_report_in_a_folder_that_does_not_exist(tmp_path, capsys):
    assert check_coverage.check(str(tmp_path / "nope" / "r.xml"), 80) == 1
    assert "does not exist: no report task wrote there" in capsys.readouterr().out


def test_the_listing_is_capped(tmp_path, capsys):
    for number in range(25):
        report(tmp_path / "k" / f"r{number:02d}.xml", 1, 1)
    assert check_coverage.check(str(tmp_path / "k" / "missing.xml"), 80) == 1
    out = capsys.readouterr().out
    assert "first 20 of 25" in out
    assert "r19.xml" in out
    assert "r20.xml" not in out


def test_a_path_cannot_forge_a_workflow_command(tmp_path, capsys):
    assert check_coverage.check(str(tmp_path / "a%b\n::error::forged.xml"), 80) == 1
    out = capsys.readouterr().out
    assert len(out.splitlines()) == 1
    assert "%0A::error::forged" in out
    assert "a%25b" in out


def test_zero_lines(tmp_path, capsys):
    assert check_coverage.check(report(tmp_path / "r.xml", 0, 0), 0) == 1
    assert "no coverage data (0 lines)" in capsys.readouterr().out


def test_malformed_xml(tmp_path, capsys):
    bad = tmp_path / "r.xml"
    bad.write_text("<report><counter", encoding="utf-8")
    assert check_coverage.check(str(bad), 0) == 1
    assert "cannot read" in capsys.readouterr().out


def test_a_report_without_a_line_counter(tmp_path, capsys):
    bad = tmp_path / "r.xml"
    bad.write_text('<report><counter type="BRANCH" missed="1" covered="1"/></report>', encoding="utf-8")
    assert check_coverage.check(str(bad), 0) == 1
    assert "no LINE counter" in capsys.readouterr().out


def test_main_reads_the_environment(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["check_coverage.py"])
    monkeypatch.setenv("COVERAGE_XML_PATH", report(tmp_path / "r.xml", 2, 1))
    monkeypatch.setenv("COVERAGE_THRESHOLD", "60")
    assert check_coverage.main() == 0


@pytest.mark.parametrize("value", ["nan", "NaN", "inf", "-inf", "Infinity", "1e999"])
def test_main_refuses_a_threshold_that_is_not_finite_instead_of_passing_every_report(tmp_path, monkeypatch, capsys, value):
    """`nan` compares false with everything, so `percent < nan` would let a 10% report through."""
    monkeypatch.setattr("sys.argv", ["check_coverage.py"])
    monkeypatch.setenv("COVERAGE_XML_PATH", report(tmp_path / "r.xml", 1, 9))
    monkeypatch.setenv("COVERAGE_THRESHOLD", value)
    assert check_coverage.main() == 1
    assert "::error::coverage-threshold: must be a finite number" in capsys.readouterr().out


@pytest.mark.parametrize("value", [None, "", "eighty", "nan-ish"])
def test_main_refuses_a_threshold_that_is_not_a_number(tmp_path, monkeypatch, capsys, value):
    monkeypatch.setattr("sys.argv", ["check_coverage.py"])
    monkeypatch.setenv("COVERAGE_XML_PATH", report(tmp_path / "r.xml", 2, 1))
    if value is None:
        monkeypatch.delenv("COVERAGE_THRESHOLD", raising=False)
    else:
        monkeypatch.setenv("COVERAGE_THRESHOLD", value)
    assert check_coverage.main() == 1
    assert "::error::coverage-threshold: must be a finite number" in capsys.readouterr().out
