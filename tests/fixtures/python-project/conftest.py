"""Tier rule every Condor Python project applies: the directory under tests/ is the test's marker."""

from pathlib import Path

import pytest

_TIERS = ("unit", "integration_mock", "integration_real", "e2e")


def pytest_collection_modifyitems(items):
    """Mark each test with the tier directory right under its tests/ directory."""
    for item in items:
        parts = Path(str(item.fspath)).parts
        for i, part in enumerate(parts[:-1]):
            if part == "tests" and parts[i + 1] in _TIERS:
                item.add_marker(getattr(pytest.mark, parts[i + 1]))
                break
