from rustiter import rter


class Counter:
    def __init__(self, x=0) -> None:
        self.c = x

    def add(self):
        self.c += 1


def test_shallow_clone():
    a = rter([Counter(3)])
    clone = a.clone()
    next(clone).add()
    assert next(a).c == 4  # The rter clone points to the same element.


def test_deep_copy():
    a = rter([Counter(3)])
    clone = a.deepcopy()
    next(clone).add()
    assert next(a).c == 3  # The rter deepcopy points to the different element.
