"""Regression tests for bugs documented in the code review report (section 2)."""

from rustiter import rter


def test_filter_map_keeps_falsy_non_none_values():
    # P0-1: filter(None, ...) dropped 0, "", [], False
    ret = (
        rter([1, 0, 2, "", [], False, None])
        .filter_map(lambda x: None if x is None else x)
        .collect()
    )
    assert ret == [1, 0, 2, "", [], False]


def test_find_map_returns_falsy_first_match():
    # P0-1: find_map delegated to filter_map and skipped 0
    assert rter([0, 5]).find_map(lambda x: x) == 0
