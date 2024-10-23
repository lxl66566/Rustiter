from timeit import timeit

from src import rter

print("benchmark 1")


def rustiter():
    temp = (
        rter([3, 2, 1]).sorted().map(lambda x: x * 2).filter(lambda x: x > 3).collect()
    )
    return temp


def normal():
    temp = list(filter(lambda x: x > 3, map(lambda x: x * 2, sorted([3, 2, 1]))))
    return temp


print("rter: ", timeit("rustiter()", globals=globals(), number=10000))
print("normal: ", timeit("normal()", globals=globals(), number=10000))
