from __future__ import annotations

import itertools
from collections.abc import Iterable
from copy import deepcopy
from functools import reduce
from itertools import islice
from typing import (
    Any,
    Callable,
    Generic,
    Iterator,
    Optional,
    TypeVar,
)

T = TypeVar("T")
U = TypeVar("U")


class IterableWrapper(Generic[T]):
    def __init__(self, iterable: Iterable[T]):
        if not isinstance(iterable, Iterable):
            raise TypeError("Object must be iterable")
        self.iterator: Iterator[T] = iter(iterable)

    def advance_by(self, n: int):
        """
        [Mut ; retains = the rest elements after the first n]

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

    def all(self, predicate: Callable[[T], bool]):
        """
        [Mut]

        Returns True if all elements in the iterator satisfy the predicate.

        >>> rter([1, 2, 3, 4]).all(lambda x: x > 0)
        True
        >>> rter([1, 2, 3, 4]).all(lambda x: x > 2)
        False
        """
        return all(self.map(predicate))

    def any(self, predicate: Callable[[T], bool]):
        """
        [Mut]

        Returns True if any element in the iterator satisfies the predicate.

        >>> rter([1, 2, 3]).all(lambda x: x > 0)
        True
        >>> rter([1, 2, 3]).all(lambda x: x > 5)
        False
        """
        return any(self.map(predicate))

    # def array_chunks(self, chunk_size):
    # def by_ref(self):

    def chain(self, *iterables: Iterable[T]):
        """
        [Consume]

        chains the iterables

        >>> rter([1, 2, 3]).chain(rter([4, 5, 6])).collect()
        [1, 2, 3, 4, 5, 6]
        """
        return IterableWrapper(itertools.chain(self.iterator, *iterables))

    # def cmp(self, other):
    # def cmp_by(self, func):

    def clone(self):
        """
        [UnMut]

        returns the *shallow copy* of the iterator
        """
        self.iterator, tmp = itertools.tee(self.iterator)
        return IterableWrapper(tmp)

    def cloned(self):
        """
        [UnMut]

        returns the *deepcopy* (copy.deepcopy) of the iterator
        """
        return IterableWrapper(deepcopy(self.iterator))

    def collect(self, container: type = list):
        """
        [Consume]

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
        [UnMut]

        alias of `clone`
        """
        return self.clone()

    def count(self):
        """
        [Consume]

        Counting the number of iterations and returning it.

        >>> rter([1, 2, 3, 4]).count()
        4
        """
        return sum(1 for _ in self.iterator)

    def cycle(self):
        """
        [Consume]

        Repeats an iterator endlessly.

        >>> rter([1, 2, 3]).cycle().take(10).collect()
        [1, 2, 3, 1, 2, 3, 1, 2, 3, 1]
        """
        return IterableWrapper(itertools.cycle(self.iterator))

    def deepcopy(self):
        """
        [UnMut]

        alias of `cloned`
        """
        return self.cloned()

    @staticmethod
    def empty():
        """
        Returns an empty rter
        """
        return IterableWrapper([])

    def enumerate(self, start=0):
        """
        [Consume]

        Returns an iterable of tuples, where each tuple contains the index and the element.

        >>> rter([1, 2, 3]).enumerate().collect()
        [(0, 1), (1, 2), (2, 3)]
        >>> rter("abc").enumerate(start=1).collect()
        [(1, 'a'), (2, 'b'), (3, 'c')]
        """
        return IterableWrapper(enumerate(self.iterator, start))

    def eq(self, other) -> bool:
        """
        [UnMut]

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
        [Consume]

        Filters the iterable by applying a function to each element and keeping only those
        for which the function returns True.

        >>> rter([1, 2, 3, 4]).filter(lambda x: x % 2 == 0).collect()
        [2, 4]
        """
        return IterableWrapper(filter(func, self.iterator))

    def filter_map(self, func: Callable[[T], U]):
        """
        [Consume]

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
        [Mut ; retains = the rest elements after the finded one]

        Returns the first element in the iterable that satisfies the given predicate.
        Returns None if no such element is found.

        >>> rter([1, 2, 3, 4]).find(lambda x: x % 2 == 0)
        2
        >>> rter("hello").find(lambda x: x == 'l')
        'l'
        >>> rter([1, 2, 3]).find(lambda x: x > 5)
        """
        return next(filter(predicate, self.iterator), None)

    def find_map(self, func: Callable[[T], U]):
        """
        [Mut]

        Applies a function to each element and returns the first non-None result.
        Returns None if all function results are None.
        `iter.find_map(f)` is equivalent to `iter.filter_map(f).next()`.

        >>> rter([1, 2, 3, 4]).find_map(lambda x: x * 2 if x % 2 == 0 else None)
        4
        >>> rter("hello").find_map(lambda x: x.upper() if x in 'aeiou' else None)
        'E'
        >>> rter([1, 2, 3]).find_map(lambda x: None)
        """
        return next(self.filter_map(func), None)

    def flat_map(self, func: Callable):
        """
        [Consume]

        Applies a function to each element and flattens the resulting iterable of iterables into a single iterable.

        >>> rter([1, 2, 3]).flat_map(lambda x: [x, x * 2]).collect()
        [1, 2, 2, 4, 3, 6]
        >>> rter("hello").flat_map(lambda x: [x.upper(), x.lower()]).collect()
        ['H', 'h', 'E', 'e', 'L', 'l', 'L', 'l', 'O', 'o']
        """
        return IterableWrapper(itertools.chain.from_iterable(map(func, self.iterator)))

    def flatten(self):
        """
        [Consume]

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
        [Consume]

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
        [Mut ; retains = the rest elements after the first None]

        Creates an iterator which ends after the first None.

        >>> rter([1, 2, None, 3, 5]).fuse().collect()
        [1, 2]
        """
        return self.take_while(lambda x: x is not None)

    def ge(self, other) -> bool:
        """
        [UnMut]

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

    def gt(self, other) -> bool:
        """
        [UnMut]

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
        [UnMut]

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
        [Consume]

        Creates a new iterator which places a copy of separator between adjacent items of the original iterator.

        >>> rter([1, 2, 3]).intersperse(0).collect()
        [1, 0, 2, 0, 3]
        >>> rter("hello").intersperse('-').collect()
        ['h', '-', 'e', '-', 'l', '-', 'l', '-', 'o']
        >>> rter([]).intersperse('-').collect()
        []
        """
        return self.intersperse_with(lambda: sep)

    def intersperse_with(self, func: Callable[[], T]):
        """
        [Consume]

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

    def is_empty(self) -> bool:
        """
        [UnMut]

        Checks if the iterator is empty.

        >>> rter([]).is_empty()
        True
        >>> rter([1]).is_empty()
        False
        """
        try:
            next(self.clone())
            return False
        except StopIteration:
            return True

    def is_partitioned(self, predicate: Callable[[T], bool]):
        """
        [Consume]

        Checks if the elements of this iterator are partitioned according to the given predicate, such that all those that return true precede all those that return false.

        >>> rter("Iterator").is_partitioned(str.isupper)
        True
        >>> rter("Iterator").is_partitioned(str.islower)
        False
        >>> rter("IntoIterator").is_partitioned(str.isupper)
        False
        """
        for item in self.iterator:
            if not predicate(item):
                break
        return all(not predicate(item) for item in self.iterator)

    def is_sorted(self):
        """
        [Consume]

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
        [Consume]

        Checks if the elements of this iterator are sorted using the given comparator function.
        """
        it1, it2 = itertools.tee(self.iterator)
        next(it2, None)
        return all(func(a, b) for a, b in zip(it1, it2))

    def is_sorted_by_key(self, f: Callable):
        """
        [Consume]

        Checks if the elements of this iterator are sorted using the given key extraction function.

        Instead of comparing the iterator’s elements directly, this function compares the keys of the elements, as determined by f.

        >>> rter(["aaa", "ccc", "bbbbb"]).is_sorted_by_key(len)
        True
        """
        return self.is_sorted_by(lambda x, y: f(x) <= f(y))

    def last(self) -> Optional[T]:
        """
        [Consume]

        Returns the last element.

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

    def le(self, other) -> bool:
        """
        [UnMut]

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

    def lt(self, other) -> bool:
        """
        [UnMut]

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

    def map(self, func: Callable[[T], U]):
        """
        [Consume]

        Applies a function to each element of the iterable.

        >>> rter([1, 2]).map(lambda x: x * 2).collect()
        [2, 4]
        """
        return IterableWrapper(map(func, self.iterator))

    def map_while(self, func: Callable[[T], U]):
        """
        [Consume]

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

    def map_windows(self, n, func: Callable[[list[T]], U]):
        """
        [Consume]

        Calls the given function f for each contiguous window of size N over self and returns an iterator over the outputs of f.

        Example:
        >>> rter(['a', 'b', 'c', 'd']).map_windows(2, lambda x: ''.join(x)).collect()
        ['ab', 'bc', 'cd']
        >>> rter([1, 2, 3, 4, 5]).map_windows(3, lambda x: sum(x)).collect()
        [6, 9, 12]
        """

        def inner():
            window = []
            for item in self.iterator:
                window.append(item)
                if len(window) == n:
                    yield func(window.copy())
                    window.pop(0)

        return IterableWrapper(inner())

    def max(self):
        """
        [Consume]

        Returning the maximum element.

        >>> rter([1, 2, 3, 4]).max()
        4
        >>> rter("hello").max()
        'o'
        """
        return max(self.iterator, default=None)  # type: ignore

    # def max_by(self, f):

    def max_by_key(self, func: Callable[[T], Any]):
        """
        [Consume]

        Returning the maximum element by mapping the key using the given function.

        >>> rter(["aaa", "ccc", "bbbbb"]).max_by_key(len)
        'bbbbb'
        """
        return max(self.iterator, key=func, default=None)

    def min(self):
        """
        [Consume]

        Returning the minimum element.

        >>> rter([1, 2, 3, 4]).min()
        1
        >>> rter("hello").min()
        'e'
        """
        return min(self.iterator, default=None)  # type: ignore

    # def min_by(self, f):

    def min_by_key(self, func: Callable[[T], Any]):
        """
        [Consume]

        Returning the minimum element by mapping the key using the given function.

        >>> rter(["aaa", "ccc", "bbbbb"]).min_by_key(len)
        'aaa'
        """
        return min(self.iterator, key=func, default=None)

    def ne(self, other):
        """
        [UnMut]

        Determines if the elements of this Iterator are lexicographically not equal to those of another.

        >>> rter([1]).ne(rter([1]))
        False
        >>> rter([1]).ne(rter([1, 2]))
        True
        >>> rter([1, 2]).ne(rter([1]))
        True
        >>> rter([1, 2]).ne(rter([1, 2]))
        False
        """
        return not self == other

    def next(self):
        """
        [Mut ; retains = the rest]

        Returns the next element of the iterable.

        >>> rter([1, 2, 3, 4]).next()
        1
        >>> rter("hello").next()
        'h'
        >>> rter.empty().next()
        """
        return next(self.iterator, None)

    # def next_chunk(self):

    def nth(self, n: int) -> Optional[T]:
        """
        [Mut ; retains = the rest elements after the specified index]

        Returns the nth element of the iterable.

        >>> rter([1, 2, 3, 4]).nth(2)
        3
        >>> rter("hello").nth(1)
        'e'
        """
        return next(islice(self.iterator, n, n + 1), None)

    @staticmethod
    def once(x: T):
        """
        Returns an iterator of exactly one element.
        """
        return IterableWrapper(iter([x]))

    # def partial_cmp(self, other):
    # def partial_cmp_by(self, other, f):

    def partition(self, predicate: Callable[[T], bool]):
        """
        [Consume]

        Creating two collections from it.

        The predicate passed to partition() can return true, or false. partition() returns a pair, all of the elements for which it returned true, and all of the elements for which it returned false.

        >>> rter(range(5)).partition(lambda x: x % 2 == 0)
        ([0, 2, 4], [1, 3])
        """
        l: list[T] = []  # noqa: E741
        r: list[T] = []
        for item in self.iterator:
            if predicate(item):
                l.append(item)
            else:
                r.append(item)
        return l, r

    def partition_in_place(self, predicate: Callable[[T], bool]):
        """
        [Mut ; retains = the reordered elements]

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

    def position(self, predicate: Callable[[T], bool]):
        """
        [Mut ; retains = the rest elements after the first found element]

        Searches for an element in an iterator, returning its index.

        >>> rter([1, 2, 3]).position(lambda x: x == 2)
        1
        >>> rter([1, 2, 3]).position(lambda x: x % 5 == 0)
        """
        for i, item in enumerate(self.iterator):
            if predicate(item):
                return i

    def product(self, initial=None):
        """
        [Consume]

        Iterates over the entire iterator, multiplying all the elements.

        An empty iterator returns the one value of the type.

        >>> rter([1, 2, 3]).product()
        6
        """
        return self.reduce(lambda x, y: x * y, initial)  # type: ignore

    def reduce(self, func: Callable[[T, T], T], initial=None):
        """
        [Consume]

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
        """
        [Consume]

        Returns the reversed iterator.

        >>> rter([1, 2, 3]).rev().collect()
        [3, 2, 1]
        """
        try:
            self.iterator = reversed(self.iterator)  # type: ignore
        except TypeError:
            self.iterator = reversed(list(self.iterator))
        return self

    def rposition(self, predicate):
        """
        [Consume]

        Searches for an element in an iterator from the end, returning its index.

        >>> rter([1, 2, 3, 4]).rposition(lambda x: x == 2)
        1
        >>> rter([1, 2, 3]).rposition(lambda x: x % 5 == 0)
        """
        for i, item in self.rev().enumerate():
            if predicate(item):
                return self.count()

    @staticmethod
    def repeat(x, times=None):
        """
        Returns an iterator that repeats x, the given number of times.

        >>> rter.repeat(2, 3).collect()
        [2, 2, 2]
        """
        if times is None:
            return IterableWrapper(itertools.repeat(x))
        else:
            return IterableWrapper(itertools.repeat(x, times))

    # def scan(self, func, initial=None):
    # def size_hint(self):

    def skip(self, n):
        """
        [Consume]

        Create an iterator that skips the first n elements.

        >>> rter([1, 2, 3]).skip(2).collect()
        [3]
        """
        return IterableWrapper(islice(self.iterator, n, None))

    def skip_while(self, predicate):
        """
        [Consume]

        Skips elements based on a predicate.

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

    def sorted(self, key=None, reverse=False):
        """
        [Consume]

        Sort and return itself.

        >>> rter([1, 3, 2, 4]).sorted().collect()
        [1, 2, 3, 4]
        """
        self.iterator = iter(sorted(self.iterator, key=key, reverse=reverse))  # type: ignore
        return self

    def step_by(self, step: int):
        """
        [Consume]

        Returns a new iterable containing every `step`-th element of the original iterable.

        >>> rter([1, 2, 3, 4, 5, 6]).step_by(2).collect()
        [1, 3, 5]
        >>> rter("hello").step_by(3).collect()
        ['h', 'l']
        """
        return IterableWrapper(islice(self.iterator, 0, None, step))

    def sum(self):
        """
        [Consume]

        Sums the elements of an iterator.

        >>> rter([1, 2, 3]).sum()
        6
        """

        return self.reduce(lambda x, y: x + y)  # type: ignore

    def take(self, n: int):
        """
        [Mut ; retains = the rest elements after the first n]

        Take the first `n` elements from the iterable.

        >>> rter([1, 3, 2, 4]).take(3).collect()
        [1, 3, 2]
        """
        ans = []
        while n > 0:
            try:
                ans.append(next(self.iterator))
            except StopIteration:
                break
            n -= 1
        return IterableWrapper(ans)

    def take_while(self, predicate: Callable[[T], bool]):
        """
        [Consume]

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
        [Consume]

        Converts an iterator of pairs into a pair of containers.

        >>> a, b = rter([(1, 'a'), (2, 'b'), (3, 'c')]).unzip()
        >>> list(a)
        [1, 2, 3]
        >>> list(b)
        ['a', 'b', 'c']
        """
        return zip(*self.iterator)

    def zip(self, other: Iterable[Any]):
        """
        [Consume]

        Combines two iterables into a single iterable of tuples, pairing corresponding elements from each iterable.
        The resulting iterable will be as long as the shorter of the two input iterables.

        >>> rter([1, 2, 3]).zip(rter([4, 5, 6])).collect()
        [(1, 4), (2, 5), (3, 6)]
        >>> rter("hello").zip(rter("world")).collect()
        [('h', 'w'), ('e', 'o'), ('l', 'r'), ('l', 'l'), ('o', 'd')]
        >>> rter([1, 2]).zip(rter([3, 4, 5])).collect()
        [(1, 3), (2, 4)]
        """
        return IterableWrapper(zip(self.iterator, other))

    def __iter__(self):
        return self.iterator

    def __next__(self):
        return next(self.iterator)

    def __len__(self):
        return self.count()

    def _compare(self, other: "IterableWrapper[T]"):
        """
        [UnMut]

        Helper function to compare two iterators lexicographically.

        returns 1 if a > b, -1 if a < b, 0 if equal
        """
        if not isinstance(other, IterableWrapper):
            return NotImplemented

        x, y = self.clone(), other.clone()

        while True:
            a, b = x.next(), y.next()
            if a is None or b is None:
                return (b is None) - (a is None)
            if a != b:
                return (a > b) - (a < b)  # type: ignore

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


rter = IterableWrapper

if __name__ == "__main__":
    import doctest

    doctest.testmod()
