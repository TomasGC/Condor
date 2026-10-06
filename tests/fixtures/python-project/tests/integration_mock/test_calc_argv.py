"""Integration-mock tier: main() reads a mocked command line."""

import sys

from calc import main


def test_main_reads_sys_argv_when_no_arguments_are_given(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["calc.py", "4", "5"])
    assert main() == 0
    assert capsys.readouterr().out == "9\n"
