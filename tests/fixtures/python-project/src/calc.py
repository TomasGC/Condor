"""Arithmetic for Condor's self-test: the code under test when Condor runs python-push-ci.yml on itself."""

import sys


def add(a: int, b: int) -> int:
    """Return the sum of a and b."""
    return a + b


def divide(a: float, b: float) -> float:
    """Return a divided by b; raise ValueError when b is zero."""
    if b == 0:
        raise ValueError("division by zero")
    return a / b


def main(argv: list[str] | None = None) -> int:
    """Print the sum of the two integers given as arguments."""
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        print("usage: calc.py A B", file=sys.stderr)
        return 2
    print(add(int(args[0]), int(args[1])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
