"""Sits outside every tier directory: no tier job would run it, so the collection guard must report it."""


def test_outside_every_tier():
    assert 2 * 2 == 4
