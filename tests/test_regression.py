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


def test_inspect_is_lazy():
    # P0-2: func must not run until the result is consumed
    seen = []
    rter([1, 2, 3]).inspect(seen.append)
    assert seen == []


def test_inspect_passes_real_elements():
    # P0-2: func must receive the elements themselves, not copies
    obj = object()
    seen = []
    rter([obj]).inspect(seen.append).collect()
    assert seen[0] is obj


def test_inspect_works_on_generator_chains():
    # P0-2: deepcopy of a generator raises TypeError
    seen = []
    ret = rter(x for x in [1, 2, 3]).map(lambda x: x + 1).inspect(seen.append).collect()
    assert ret == [2, 3, 4]
    assert seen == [2, 3, 4]


def test_compare_handles_none_elements():
    # P1-2: None was used both as an element and as the exhaustion sentinel
    assert rter([None, 1]).eq(rter([None])) is False
    assert rter([1, None]).eq(rter([1])) is False


def test_skip_while_keeps_none_elements():
    # P1-3: a leading None was misread as exhaustion
    assert rter([None, 2]).skip_while(lambda x: False).collect() == [None, 2]


def test_compare_accepts_plain_iterables():
    # P2-4: comparisons rejected non-IterableWrapper operands
    assert rter([1, 2]) == [1, 2]
    assert not (rter([1]) == 5)
    assert rter([1, 2]) < [1, 3]
