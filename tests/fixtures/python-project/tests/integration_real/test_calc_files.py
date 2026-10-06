"""Integration-real tier: values read from a real file."""

import pytest

from calc import add


def test_add_values_read_from_a_file(tmp_path):
    numbers = tmp_path / "numbers.txt"
    numbers.write_text("7\n8\n", encoding="utf-8")
    a, b = (int(line) for line in numbers.read_text(encoding="utf-8").split())
    assert add(a, b) == 15


@pytest.mark.local_only
def test_excluded_by_the_exclude_marker():
    """Would fail the run if the pipeline stopped deselecting `exclude-marker` tests."""
    pytest.fail("a local_only test ran in CI")
