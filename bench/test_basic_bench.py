import pytest

from rustiter import rter


def rustiter():
    temp = (
        rter([3, 2, 1]).sorted().map(lambda x: x * 2).filter(lambda x: x > 3).collect()
    )
    return temp


def normal():
    temp = list(filter(lambda x: x > 3, map(lambda x: x * 2, sorted([3, 2, 1]))))
    return temp


@pytest.mark.benchmark
def test_rustiter(benchmark):
    benchmark(rustiter)


@pytest.mark.benchmark
def test_normal(benchmark):
    benchmark(normal)
