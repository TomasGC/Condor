"""Checks the line coverage of a Kover/JaCoCo XML report against a threshold.

Input: COVERAGE_XML_PATH and COVERAGE_THRESHOLD in the environment; an optional first argument names a file that
receives `percentage=<n>` (the adapter passes the platform's output file). Exit 0 when the threshold is met.
"""
import math
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

MAX_LISTED = 20
HINT = (
    "Kover names the file report<Variant>.xml after the variant, so coverage-report-tasks and "
    "coverage-xml-path must name the same variant."
)


def escape(text: str) -> str:
    """Workflow-command escaping: a path or message can never end the annotation or start another."""
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def fail(message: str) -> int:
    print(f"::error::{escape(message)}")
    return 1


def found_next_to(report: Path) -> str:
    folder = report.parent
    if not folder.is_dir():
        return f"{folder} does not exist: no report task wrote there"
    names = sorted(str(path) for path in folder.rglob("*.xml"))
    if not names:
        return f"no .xml file under {folder}"
    more = f" (first {MAX_LISTED} of {len(names)})" if len(names) > MAX_LISTED else ""
    return f"XML files under {folder}{more}: " + ", ".join(names[:MAX_LISTED])


def line_counter(report: Path) -> tuple[int, int]:
    """(covered, missed) of the report element's own LINE counter, the project total."""
    counters = [c for c in ET.parse(report).getroot().findall("counter") if c.get("type") == "LINE"]
    if not counters:
        raise ValueError("no LINE counter at the report level")
    return int(counters[-1].get("covered")), int(counters[-1].get("missed"))


def check(path: str, threshold: float, output_file: str | None = None) -> int:
    report = Path(path)
    if not report.is_file():
        return fail(f"coverage-xml-path: no report at '{path}'. {HINT} {found_next_to(report)}")
    try:
        covered, missed = line_counter(report)
    except (ET.ParseError, ValueError) as error:
        return fail(f"coverage-xml-path: cannot read '{path}': {error}")
    total = covered + missed
    if total == 0:
        return fail(f"coverage-xml-path: no coverage data (0 lines) in '{path}'")
    percent = covered * 100 // total
    print(f"Coverage: {percent}% ({covered}/{total} lines)")
    if output_file:
        with open(output_file, "a", encoding="utf-8") as handle:
            handle.write(f"percentage={percent}\n")
    if percent < threshold:
        return fail(f"Coverage {percent}% below threshold {threshold:g}%")
    print(f"SUCCESS: Coverage {percent}% >= {threshold:g}%")
    return 0


def main() -> int:
    try:
        threshold = float(os.environ["COVERAGE_THRESHOLD"])
    except (KeyError, ValueError):
        threshold = math.nan
    if not math.isfinite(threshold):
        # nan compares false with every percentage, so a gate built on `percent < nan` would pass any report
        return fail("coverage-threshold: must be a finite number")
    return check(os.environ.get("COVERAGE_XML_PATH", ""), threshold, sys.argv[1] if len(sys.argv) > 1 else None)


if __name__ == "__main__":
    sys.exit(main())
