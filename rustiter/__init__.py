import itertools
from collections.abc import Iterable
from copy import deepcopy
from functools import reduce
from itertools import islice
from typing import Callable


class IterableWrapper:
    def __init__(self, iterable):
        if not isinstance(iterable, Iterable):
            raise TypeError("Object must be iterable")
        self.iterator = iter(iterable)

    def advance_by(self, n):
        """
        Advances the iterator by n elements.

        advance_by(n) will return None if the iterator successfully advances by n elements,
        or an int with value k if StopIteration is raised, where k is remaining number of
        steps that could not be advanced because the iterator ran out.

        >>> a = rter([1, 2, 3, 4])
        >>> a.advance_by(2)
        >>> a.next()
        3
        >>> a.advance_by(0)
        >>> a.advance_by(100)
        99
        """
        try:
            while n > 0:
                _ = next(self.iterator)
                n -= 1
        except StopIteration:
            return n

    def all(self, predicate):
        """
        Returns True if all elements in the iterator satisfy the predicate.

        >>> rter([1, 2, 3, 4]).all(lambda x: x > 0)
        True
        >>> rter([1, 2, 3, 4]).all(lambda x: x > 2)
        False
        """
        return all(predicate(item) for item in self.iterator)

    def any(self, predicate):
        """
        Returns True if any element in the iterator satisfies the predicate.

        >>> rter([1, 2, 3]).all(lambda x: x > 0)
        True
        >>> rter([1, 2, 3]).all(lambda x: x > 5)
        False
        """
        return any(predicate(item) for item in self.iterator)

    # def array_chunks(self, chunk_size):
    # def by_ref(self):

    def chain(self, *iterables):
        """
        chains the iterables

        >>> rter([1, 2, 3]).chain(rter([4, 5, 6])).collect()
        [1, 2, 3, 4, 5, 6]
        """
        return IterableWrapper(itertools.chain(self.iterator, *iterables))

    # def cmp(self, other):
    # def cmp_by(self, func):

    def clone(self):
        """
        returns the shallow copy of the iterator
        """
        self.iterator, tmp = itertools.tee(self.iterator)
        return IterableWrapper(tmp)

    def cloned(self):
        """
        returns the deepcopy (copy.deepcopy) of the iterator
        """
        return IterableWrapper(deepcopy(self.iterator))

    def collect(self, container: type = list):
        """
        collects the iterator into a container, a list by default.

        >>> rter([1, 2, 3]).collect()
        [1, 2, 3]
        >>> rter([1, 2, 3]).collect(set)
        {1, 2, 3}
        >>> rter([(1, 2), (3, 4)]).collect(dict)
        {1: 2, 3: 4}
        """
        return container(self.iterator)

    def copy(self):
        """
        alias of `clone`
        """
        return self.clone()

    def count(self):
        """
        Consumes the iterator, counting the number of iterations and returning it.

        >>> rter([1, 2, 3, 4]).count()
        4
        """
        return sum(1 for _ in self.iterator)

    def cycle(self):
        """
        Repeats an iterator endlessly.

        >>> rter([1, 2, 3]).cycle().take(10).collect()
        [1, 2, 3, 1, 2, 3, 1, 2, 3, 1]
        """
        return IterableWrapper(itertools.cycle(self.iterator))

    def deepcopy(self):
        """
        alias of `cloned`
        """
        return self.cloned()

    @staticmethod
    def empty():
        return IterableWrapper([])

    def enumerate(self, start=0):
        """
        Returns an iterable of tuples, where each tuple contains the index and the element.

        >>> rter([1, 2, 3]).enumerate().collect()
        [(0, 1), (1, 2), (2, 3)]
        >>> rter("abc").enumerate(start=1).collect()
        [(1, 'a'), (2, 'b'), (3, 'c')]
        """
        return IterableWrapper(enumerate(self.iterator, start))

    def eq(self, other):
        """
        Determines if the elements of this Iterator are equal to those of another.

        >>> rter([1]).eq(rter([1]))
        True
        >>> rter([1, 2]).eq(rter([1]))
        False
        """
        return self == other

    # def eq_by(self, other, f):
    #     """
    #     Determines if the elements of this Iterator are equal to those of another with respect to the specified equality function.
    #     """

    def filter(self, func):
        """
        Filters the iterable by applying a function to each element and keeping only those
        for which the function returns True.

        >>> rter([1, 2, 3, 4]).filter(lambda x: x % 2 == 0).collect()
        [2, 4]
        """
        return IterableWrapper(filter(func, self.iterator))

    def filter_map(self, func):
        """
        Applies a function to each element and keeps only those for which the function returns a non-None value.
        The function's return value is used as the element in the resulting iterable.

        >>> rter([1, 2, 3, 4]).filter_map(lambda x: x * 2 if x % 2 == 0 else None).collect()
        [4, 8]
        >>> rter("hello").filter_map(lambda x: x.upper() if x in 'aeiou' else None).collect()
        ['E', 'O']
        """
        return IterableWrapper(filter(None, map(func, self.iterator)))

    def find(self, predicate):
        """
        Returns the first element in the iterable that satisfies the given predicate.
        Returns None if no such element is found.

        >>> rter([1, 2, 3, 4]).find(lambda x: x % 2 == 0)
        2
        >>> rter("hello").find(lambda x: x == 'l')
        'l'
        >>> rter([1, 2, 3]).find(lambda x: x > 5)
        """
        return next(filter(predicate, self.iterator), None)

    def find_map(self, func):
        """
        Applies a function to each element and returns the first non-None result.
        Returns None if all function results are None.

        >>> rter([1, 2, 3, 4]).find_map(lambda x: x * 2 if x % 2 == 0 else None)
        4
        >>> rter("hello").find_map(lambda x: x.upper() if x in 'aeiou' else None)
        'E'
        >>> rter([1, 2, 3]).find_map(lambda x: None)
        """
        return next(self.filter_map(func), None)

    def flat_map(self, func):
        """
        Applies a function to each element and flattens the resulting iterable of iterables into a single iterable.

        >>> rter([1, 2, 3]).flat_map(lambda x: [x, x * 2]).collect()
        [1, 2, 2, 4, 3, 6]
        >>> rter("hello").flat_map(lambda x: [x.upper(), x.lower()]).collect()
        ['H', 'h', 'E', 'e', 'L', 'l', 'L', 'l', 'O', 'o']
        """
        return IterableWrapper(itertools.chain.from_iterable(map(func, self.iterator)))

    def flatten(self):
        """
        Flattens a nested iterable into a single iterable.

        >>> rter([[1, 2], [3, 4]]).flatten().collect()
        [1, 2, 3, 4]
        >>> rter([1, [2, 3], 4]).flatten().collect()
        [1, 2, 3, 4]
        >>> rter("hello").flatten().collect()
        ['h', 'e', 'l', 'l', 'o']
        """
        return IterableWrapper(
            itertools.chain.from_iterable(
                map(lambda x: x if isinstance(x, Iterable) else [x], self.iterator)
            )
        )

    def fold(self, func, initial=None):
        """
        alias of `reduce`
        """
        return self.reduce(func, initial)

    def for_each(self, func):
        """
        Applies a function to each element of the iterable, but doesn't return any values.

        >>> rter([1, 2, 3]).for_each(lambda x: print(x * 2))
        2
        4
        6
        >>> rter("hello").for_each(lambda x: print(x.upper()))
        H
        E
        L
        L
        O
        """
        for item in self.iterator:
            func(item)

    def fuse(self):
        """
        Creates an iterator which ends after the first None.

        >>> rter([1, 2, None, 3, 5]).fuse().collect()
        [1, 2]
        """
        return self.take_while(lambda x: x is not None)

    def ge(self, other):
        """
        Determines if the elements of this Iterator are lexicographically greater than or equal to those of another.

        >>> rter([1]).ge(rter([1]))
        True
        >>> rter([1]).ge(rter([1, 2]))
        False
        >>> rter([1, 2]).ge(rter([1]))
        True
        >>> rter([1, 2]).ge(rter([1, 2]))
        True
        """
        return self >= other

    def gt(self, other):
        """
        Determines if the elements of this Iterator are lexicographically greater than those of another.

        >>> rter([1]).gt(rter([1]))
        False
        >>> rter([1]).gt(rter([1, 2]))
        False
        >>> rter([1, 2]).gt(rter([1]))
        True
        >>> rter([1, 2]).gt(rter([1, 2]))
        False
        """
        return self > other

    def inspect(self, func):
        """
        Applies a function to each element of the iterable, passing the value on.
        Useful for debugging and inspecting the values in an iterator chain.

        >>> rter([1, 2, 3]).map(lambda x: x * 2).inspect(lambda x: print(f"Value: {x}")).collect()
        Value: 2
        Value: 4
        Value: 6
        [2, 4, 6]
        """
        self.cloned().for_each(func)
        return self

    def intersperse(self, sep):
        """
        Creates a new iterator which places a copy of separator between adjacent items of the original iterator.

        >>> rter([1, 2, 3]).intersperse(0).collect()
        [1, 0, 2, 0, 3]
        >>> rter("hello").intersperse('-').collect()
        ['h', '-', 'e', '-', 'l', '-', 'l', '-', 'o']
        >>> rter([]).intersperse('-').collect()
        []
        """
        return self.intersperse_with(lambda: sep)

    def intersperse_with(self, func):
        """
        Creates a new iterator which places an item generated by separator between adjacent items of the original iterator.

        The closure will be called exactly once each time an item is placed between two adjacent items from the underlying iterator; specifically, the closure is not called if the underlying iterator yields less than two items and after the last item is yielded.
        """
        try:
            first = next(self.iterator)
        except StopIteration:
            return IterableWrapper([])
        return IterableWrapper.once(first).chain(
            IterableWrapper.repeat(func()).zip(self).flatten()
        )

    def is_partitioned(self, predicate):
        """
        Checks if the elements of this iterator are partitioned according to the given predicate, such that all those that return true precede all those that return false.

        >>> rter("Iterator").is_partitioned(str.isupper)
        True
        >>> rter("IntoIterator").is_partitioned(str.isupper)
        False
        """
        for item in self.iterator:
            if not predicate(item):
                break
        return all(not predicate(item) for item in self.iterator)

    def is_sorted(self):
        """
        Checks if the iterable is sorted according to the given key function and sorting order.

        >>> rter([1, 2, 3, 4]).is_sorted()
        True
        >>> rter([4, 3, 2, 1]).is_sorted()
        False
        >>> rter([1, 3, 2, 4]).is_sorted()
        False
        >>> rter(["apple", "banana", "cherry"]).is_sorted()
        True
        """
        return self.is_sorted_by(lambda x, y: x <= y)

    def is_sorted_by(self, func: Callable):
        """
        Checks if the elements of this iterator are sorted using the given comparator function.
        """
        it1, it2 = itertools.tee(self.iterator)
        next(it2, None)
        return all(func(a, b) for a, b in zip(it1, it2))

    def is_sorted_by_key(self, f: Callable):
        """
        Checks if the elements of this iterator are sorted using the given key extraction function.

        Instead of comparing the iterator’s elements directly, this function compares the keys of the elements, as determined by f.

        >>> rter(["aaa", "ccc", "bbbbb"]).is_sorted_by_key(len)
        True
        """
        return self.is_sorted_by(lambda x, y: f(x) <= f(y))

    def last(self):
        """
        Consumes the iterator, returning the last element.

        >>> rter([1, 2, 3]).last()
        3
        >>> rter([]).last()
        """
        try:
            return next(reversed(self.iterator), None)  # type: ignore
        except:  # noqa: E722
            last = None
            try:
                for item in self.iterator:
                    last = item
            except StopIteration:
                pass
            return last

    def le(self, other):
        """
        Determines if the elements of this Iterator are lexicographically less or equal to those of another.

        >>> rter([1]).le(rter([1]))
        True
        >>> rter([1]).le(rter([1, 2]))
        True
        >>> rter([1, 2]).le(rter([1]))
        False
        >>> rter([1, 2]).le(rter([1, 2]))
        True
        """
        return self <= other

    def lt(self, other):
        """
        Determines if the elements of this Iterator are lexicographically less than those of another.

        >>> rter([1]).lt(rter([1]))
        False
        >>> rter([1]).lt(rter([1, 2]))
        True
        >>> rter([1, 2]).lt(rter([1]))
        False
        >>> rter([1, 2]).lt(rter([1, 2]))
        False
        """
        return self < other

    def map(self, func):
        """
        Applies a function to each element of the iterable.

        >>> rter([1, 2]).map(lambda x: x * 2).collect()
        [2, 4]
        """
        return IterableWrapper(map(func, self.iterator))

    def map_while(self, func):
        """
        Applies the function `func` to each element of the iterator and yields the result.
        Stops when the function returns `None`.

        >>> rter([-1, 4, 0, 1]).map_while(lambda x: x + 2 if x != 0 else None).collect()
        [1, 6]
        """

        def inner():
            for item in self.iterator:
                result = func(item)
                if result is None:
                    break
                yield result

        return IterableWrapper(inner())

    def map_windows(self, n):
        """
        Yields sliding windows of size `n` from the iterator.

        Example:
        >>> rter(['a', 'b', 'c', 'd']).map_windows(2).collect()
        [['a', 'b'], ['b', 'c'], ['c', 'd']]
        >>> rter([1, 2, 3, 4, 5]).map_windows(3).collect()
        [[1, 2, 3], [2, 3, 4], [3, 4, 5]]
        """

        def inner():
            window = []
            for item in self.iterator:
                window.append(item)
                if len(window) == n:
                    yield window.copy()
                    window.pop(0)

        return IterableWrapper(inner())

    def max(self):
        return max(self.iterator, default=None)

    def max_by(self, func):
        return max(self.iterator, key=func, default=None)

    # def max_by_key(self, f):

    def min(self):
        return min(self.iterator, default=None)

    def min_by(self, func):
        return min(self.iterator, key=func, default=None)

    # def min_by_key(self, f):

    def ne(self, other):
        return not self == other

    def next(self):
        return next(self.iterator)

    # def next_chunk(self):

    def nth(self, n):
        """
        Returns the nth element of the iterable.

        >>> rter([1, 2, 3, 4]).nth(2)
        3
        >>> rter("hello").nth(1)
        'e'
        """
        return next(islice(self.iterator, n, n + 1), None)

    @staticmethod
    def once(x):
        """
        Returns an iterator of exactly one element.
        """
        return IterableWrapper(iter([x]))

    # def partial_cmp(self, other):
    # def partial_cmp_by(self, other, f):

    def partition(self, predicate):
        """
        Consumes an iterator, creating two collections from it.

        The predicate passed to partition() can return true, or false. partition() returns a pair, all of the elements for which it returned true, and all of the elements for which it returned false.

        >>> rter(range(5)).partition(lambda x: x % 2 == 0)
        ([0, 2, 4], [1, 3])
        """
        l, r = [], []  # noqa: E741
        for item in self.iterator:
            if predicate(item):
                l.append(item)
            else:
                r.append(item)
        return l, r

    def partition_in_place(self, predicate):
        """
        Reorders the elements of this iterator in-place according to the given predicate, such that all those that return true precede all those that return false. Returns the number of true elements found.

        The relative order of partitioned items is not maintained.

        >>> a = rter(range(5))
        >>> a.partition_in_place(lambda x: x % 2 == 0)
        3
        >>> a.collect()
        [0, 2, 4, 1, 3]
        """
        l, r = self.partition(predicate)  # noqa: E741
        size = len(l)
        self.iterator = itertools.chain(l, r)
        return size

    # def peekable(self):

    def position(self, predicate):
        """
        Searches for an element in an iterator, returning its index.

        >>> rter([1, 2, 3]).position(lambda x: x == 2)
        1
        >>> rter([1, 2, 3]).position(lambda x: x % 5 == 0)
        """
        for i, item in enumerate(self.iterator):
            if predicate(item):
                return i
        return None

    def product(self):
        """
        Iterates over the entire iterator, multiplying all the elements.

        An empty iterator returns the one value of the type.

        >>> rter([1, 2, 3]).product()
        6
        """
        return reduce(lambda x, y: x * y, self.iterator, 1)

    def reduce(self, func, initial=None):
        """
        Reduces the elements to a single one, by repeatedly applying a reducing operation.

        If the iterator is empty, returns None; otherwise, returns the result of the reduction.

        The reducing function is a closure with two arguments: an ‘accumulator’, and an element.

        >>> rter([1, 2, 3]).reduce(lambda x, y: x + y)
        6
        >>> rter([1, 2, 3]).reduce(lambda x, y: x + y, 994)
        1000
        >>> rter([]).reduce(lambda x, y: x + y, 994)
        994
        """
        if initial is None:
            return reduce(func, self.iterator)
        return reduce(func, self.iterator, initial)

    def rev(self):
        return IterableWrapper(reversed(self.iterator))  # type: ignore

    def rposition(self, predicate):
        return self.rev().position(predicate)

    @staticmethod
    def repeat(x, times=None):
        if times is None:
            return IterableWrapper(itertools.repeat(x))
        else:
            return IterableWrapper(itertools.repeat(x, times))

    # def scan(self, func, initial=None):
    # def size_hint(self):

    def skip(self, n):
        """
        Creates an iterator that skips the first n elements.

        >>> rter([1, 2, 3]).skip(2).collect()
        [3]
        """
        return IterableWrapper(islice(self.iterator, n, None))

    def skip_while(self, predicate):
        """
        Creates an iterator that skips elements based on a predicate.

        >>> rter([1, 2, 3, 4, 5]).skip_while(lambda x: x < 3).collect()
        [3, 4, 5]
        """
        n = None
        try:
            n = next(self.iterator)
            while predicate(n):
                n = next(self.iterator)
        except StopIteration:
            return IterableWrapper.empty()
        if n is not None:
            return IterableWrapper.once(n).chain(self)
        else:
            return IterableWrapper([])

    def sorted(self):
        """
        Return the sorted iterator.

        >>> rter([1, 3, 2, 4]).sorted().collect()
        [1, 2, 3, 4]
        """
        return IterableWrapper(sorted(self.iterator))

    def step_by(self, step):
        """
        Returns a new iterable containing every `step`-th element of the original iterable.

        >>> rter([1, 2, 3, 4, 5, 6]).step_by(2).collect()
        [1, 3, 5]
        >>> rter("hello").step_by(3).collect()
        ['h', 'l']
        """
        return IterableWrapper(islice(self.iterator, 0, None, step))

    def sum(self):
        """
        Sums the elements of an iterator.

        >>> rter([1, 2, 3]).sum()
        6
        """

        return self.reduce(lambda x, y: x + y, 0)

    def take(self, n):
        """
        Take the first `n` elements from the iterable.

        >>> rter([1, 3, 2, 4]).take(3).collect()
        [1, 3, 2]
        """
        return IterableWrapper(islice(self.iterator, n))

    def take_while(self, predicate):
        """
        Returns an iterable containing elements from the original iterable as long as the predicate returns True.
        Stops taking elements as soon as the predicate returns False.

        >>> rter([1, 2, 3, 4, 5]).take_while(lambda x: x < 3).collect()
        [1, 2]
        >>> rter("hello").take_while(lambda x: x != 'l').collect()
        ['h', 'e']
        """
        return IterableWrapper(itertools.takewhile(predicate, self.iterator))

    # def try_collect():
    # def try_find():
    # def try_fold():
    # def try_for_each():
    # def try_reduce():

    def unzip(self):
        """
        Converts an iterator of pairs into a pair of containers.

        >>> a, b = rter([(1, 'a'), (2, 'b'), (3, 'c')]).unzip()
        >>> list(a)
        [1, 2, 3]
        >>> list(b)
        ['a', 'b', 'c']
        """
        return zip(*self.iterator)

    def zip(self, other):
        """
        Combines two iterables into a single iterable of tuples, pairing corresponding elements from each iterable.
        The resulting iterable will be as long as the shorter of the two input iterables.

        >>> rter([1, 2, 3]).zip(rter([4, 5, 6])).collect()
        [(1, 4), (2, 5), (3, 6)]
        >>> rter("hello").zip(rter("world")).collect()
        [('h', 'w'), ('e', 'o'), ('l', 'r'), ('l', 'l'), ('o', 'd')]
        >>> rter([1, 2]).zip(rter([3, 4, 5])).collect()
        [(1, 3), (2, 4)]
        """
        return IterableWrapper(zip(self.iterator, other.iterator))

    def __iter__(self):
        return self.iterator

    def __next__(self):
        return next(self.iterator)

    def __len__(self):
        return self.count()

    def _compare(self, other):
        """Helper function to compare two iterators lexicographically."""
        if not isinstance(other, IterableWrapper):
            return NotImplemented

        while True:
            a, b = next(self.iterator, None), next(other.iterator, None)
            if a is None or b is None:
                return (b is None) - (a is None)
            if a != b:
                return (a > b) - (a < b)  # returns 1 if a > b, -1 if a < b, 0 if equal
        return 0

    def __eq__(self, other):
        return self._compare(other) == 0

    def __lt__(self, other):
        return self._compare(other) < 0

    def __le__(self, other):
        return self._compare(other) <= 0

    def __gt__(self, other):
        return self._compare(other) > 0

    def __ge__(self, other):
        return self._compare(other) >= 0


def rter(x):
    return IterableWrapper(x)


if __name__ == "__main__":
    import doctest

    doctest.testmod()
