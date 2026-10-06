"""Unit tier: pure functions."""

import pytest

from calc import add, divide, main


def test_add_returns_the_sum():
    assert add(2, 3) == 5


def test_divide_returns_the_quotient():
    assert divide(6, 3) == 2


def test_divide_by_zero_raises():
    with pytest.raises(ValueError, match="division by zero"):
        divide(1, 0)


def test_main_prints_the_sum(capsys):
    assert main(["2", "3"]) == 0
    assert capsys.readouterr().out == "5\n"


def test_main_rejects_a_wrong_argument_count(capsys):
    assert main(["2"]) == 2
    assert "usage" in capsys.readouterr().err
