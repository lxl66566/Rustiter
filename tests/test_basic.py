from src import rter


def test_basic():
    """
    This test contains some basic operations to the rustiter.
    """
    ret = (
        rter(range(10))
        .filter(lambda x: x % 2 == 0)
        .map(lambda x: x + 1)
        .take(3)
        .collect()
    )
    assert ret == [1, 3, 5]
    assert rter(range(10)).reduce(lambda x, y: x + y, 0) == 45

