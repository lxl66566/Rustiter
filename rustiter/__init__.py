import heapq
import itertools
import math
from collections import deque
from collections.abc import Iterable as ABCIterable
from copy import deepcopy
from functools import cmp_to_key, reduce
from itertools import islice
from operator import length_hint
from typing import (
    Any,
    Callable,
    Generic,
    Iterable,
    Iterator,
    List,
    Optional,
    Tuple,
    TypeVar,
    Union,
)

T = TypeVar("T")
U = TypeVar("U")
S = TypeVar("S")

# Module-level sentinel distinguishing "argument not given" from an explicit None.
_SENTINEL = object()


class IterableWrapper(Generic[T]):
    __slots__ = ("iterator",)

    def __init__(self, iterable: Iterable[T]):
        self.iterator: Iterator[T] = iter(iterable)

    def advance_by(self, n: int):
        """
        [Mut ; retains = the rest elements after the first n]

        Advances the iterator by n elements.

        advance_by(n) will return None if the iterator successfully advances by n elements,
        or an int with value k if StopIteration is raised, where k is remaining number of
        steps that could not be advanced because the iterator ran out.

        Negative n raises ValueError (Rust panics; this library uses the explicit ValueError policy shared with step_by).

        >>> a = rter([1, 2, 3, 4])
        >>> a.advance_by(2)
        >>> a.next()
        3
        >>> a.advance_by(0)
        >>> a.advance_by(100)
        99
        >>> rter([1, 2]).advance_by(-1)
        Traceback (most recent call last):
            ...
        ValueError: advance_by() requires n >= 0
        """
        if n < 0:
            raise ValueError("advance_by() requires n >= 0")
        try:
            while n > 0:
                _ = next(self.iterator)
                n -= 1
        except StopIteration:
            return n

    def advance_back_by(self, n: int):
        """
        [Consume]

        Advances the iterator by n elements from the end.

        Returns None on success, or the number k of remaining steps that could not be
        advanced because the iterator ran out, mirroring `advance_by`.

        Python iterators cannot go backwards, so the iterator is materialized first;
        the elements before the skipped ones are kept in self.

        >>> a = rter([1, 2, 3, 4])
        >>> a.advance_back_by(2)
        >>> a.collect()
        [1, 2]
        >>> rter([1]).advance_back_by(3)
        2
        """
        items = list(self.iterator)
        if n > len(items):
            self.iterator = iter([])
            return n - len(items)
        self.iterator = iter(items[: len(items) - n])

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

        >>> rter([1, 2, 3]).any(lambda x: x > 0)
        True
        >>> rter([1, 2, 3]).any(lambda x: x > 5)
        False
        """
        return any(self.map(predicate))

    # def array_chunks(self, chunk_size):

    def by_ref(self):
        """
        [UnMut]

        Returns the iterator itself.

        Python iterators are already passed by reference; this method exists only for API parity with Rust.

        >>> a = rter([1, 2, 3])
        >>> a.by_ref() is a
        True
        """
        return self

    def chain(self, *iterables: Iterable[T]):
        """
        [Consume]

        chains the iterables

        >>> rter([1, 2, 3]).chain(rter([4, 5, 6])).collect()
        [1, 2, 3, 4, 5, 6]
        """
        return IterableWrapper(itertools.chain(self.iterator, *iterables))

    def chunk_by(self, key: Callable[[T], Any]) -> "IterableWrapper[List[T]]":
        """
        [Consume]

        Groups consecutive elements sharing the same key into lists.

        Unlike a full grouping, non-adjacent elements with the same key are not merged.
        Each chunk is materialized, but the chunks themselves are produced lazily.

        >>> rter([1, 1, 2, 2, 1]).chunk_by(lambda x: x).collect()
        [[1, 1], [2, 2], [1]]
        >>> rter(["apple", "avocado", "banana", "cherry"]).chunk_by(lambda s: s[0]).collect()
        [['apple', 'avocado'], ['banana'], ['cherry']]
        """
        return IterableWrapper(list(g) for _, g in itertools.groupby(self.iterator, key))

    def cmp(self, other) -> int:
        """
        [UnMut]

        Lexicographically compares the elements of two iterators.

        Returns -1, 0 or 1 as this iterator is less than, equal to, or greater than `other`.

        >>> rter([1, 2, 3]).cmp(rter([1, 2, 4]))
        -1
        >>> rter([1, 2, 3]).cmp(rter([1, 2, 3]))
        0
        >>> rter([1, 2]).cmp(rter([1]))
        1
        """
        if not isinstance(other, IterableWrapper):
            other = IterableWrapper(other)
        return self._compare(other)  # type: ignore

    def cmp_by(self, other, func: Callable[[T, T], int]) -> int:
        """
        [UnMut]

        Lexicographically compares the elements of two iterators using the given comparator.

        `func(a, b)` must return -1, 0 or 1 as `a` is less than, equal to, or greater than `b`.

        >>> rter([1, 2, 3]).cmp_by(rter([1, 2, 4]), lambda a, b: (a > b) - (a < b))
        -1
        >>> rter(["a", "b"]).cmp_by(["a", "c"], lambda a, b: (a > b) - (a < b))
        -1
        """
        y = other if isinstance(other, IterableWrapper) else IterableWrapper(other)
        x, y = self.clone(), y.clone()
        exhausted = object()
        while True:
            a = next(x, exhausted)
            b = next(y, exhausted)
            if a is exhausted or b is exhausted:
                return (b is exhausted) - (a is exhausted)
            ordering = func(a, b)
            if ordering != 0:
                return ordering

    def clone(self):
        """
        [UnMut]

        Returns a *shallow copy* of the iterator (via `itertools.tee`); the original and the copy draw from the same source. Copies the iterator object, not the elements (see README "Differences from Rust").

        >>> a = rter([1, 2, 3])
        >>> a.clone().collect()
        [1, 2, 3]
        >>> a.collect()
        [1, 2, 3]
        """
        self.iterator, tmp = itertools.tee(self.iterator)
        return IterableWrapper(tmp)

    def cloned(self):
        """
        [UnMut]

        Returns a *deepcopy* (copy.deepcopy) of the iterator, duplicating its current state. This differs from Rust's `cloned`, which clones each element; see README "Differences from Rust".

        deepcopy relies on pickling the internal iterator: it works for C-implemented iterators (list_iterator / map / filter / enumerate, ...) but raises TypeError for generator chains.

        >>> a = rter([1, 2, 3])
        >>> a.cloned().collect()
        [1, 2, 3]
        >>> a.collect()
        [1, 2, 3]
        """
        return IterableWrapper(deepcopy(self.iterator))

    def collect(self, container: Union[Callable[[Iterable[Any]], Any], type] = list):
        """
        [Consume]

        Collects the iterator into a container (a list by default), or any function that receives an iterator as an argument.

        >>> rter([1, 2, 3]).collect()
        [1, 2, 3]
        >>> rter([1, 2, 3]).collect(set)
        {1, 2, 3}
        >>> rter([(1, 2), (3, 4)]).collect(dict)
        {1: 2, 3: 4}
        >>> rter(["h", "e", "l", "l", "o"]).collect("".join)
        'hello'
        """
        return container(self.iterator)

    def copy(self):
        """
        [UnMut]

        Alias of `clone`; like it, this copies the iterator object (tee), not each element, unlike Rust's `copied`.

        >>> rter([1, 2]).copy().collect()
        [1, 2]
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

        Alias of `cloned`; see `cloned` for the divergence from Rust and the generator-chain limitation.

        >>> rter([1, 2]).deepcopy().collect()
        [1, 2]
        """
        return self.cloned()

    @staticmethod
    def empty():
        """
        Returns an empty rter

        >>> rter.empty().collect()
        []
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
        >>> rter([None, 1]).eq(rter([None]))
        False
        >>> rter([1, None]).eq(rter([1]))
        False
        >>> rter([1, 2]) == [1, 2]
        True
        >>> rter([1]) == 5
        False
        """
        return self == other

    def eq_by(self, other, f: Callable[[T, T], bool]) -> bool:
        """
        [UnMut]

        Determines if the elements of this Iterator are equal to those of another with respect to the specified equality function.

        >>> rter([1, 2, 3]).eq_by(rter([1, 5, 3]), lambda a, b: a == b)
        False
        >>> rter([1, 2, 3]).eq_by(rter([3, 4, 7]), lambda a, b: a % 2 == b % 2)
        True
        >>> rter([1, 2]).eq_by(rter([1, 2, 3]), lambda a, b: True)
        False
        """
        y = other if isinstance(other, IterableWrapper) else IterableWrapper(other)
        x, y = self.clone(), y.clone()
        exhausted = object()
        while True:
            a = next(x, exhausted)
            b = next(y, exhausted)
            if a is exhausted or b is exhausted:
                return a is exhausted and b is exhausted
            if not f(a, b):
                return False

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
        >>> rter([1, 0, 2, "", [], False, None]).filter_map(lambda x: None if x is None else x).collect()
        [1, 0, 2, '', [], False]
        """

        def inner():
            for x in self.iterator:
                r = func(x)
                if r is not None:
                    yield r

        return IterableWrapper(inner())

    def find(self, predicate):
        """
        [Mut ; retains = the rest elements after the found one]

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
        >>> rter([0, 5]).find_map(lambda x: x)
        0
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
                map(lambda x: x if isinstance(x, ABCIterable) else [x], self.iterator)
            )
        )

    def fold(self, func, initial=_SENTINEL):
        """
        alias of `reduce`

        >>> rter([1, 2, 3]).fold(lambda x, y: x + y)
        6
        >>> rter([1, 2, 3]).fold(lambda x, y: x + y, 10)
        16
        >>> rter([]).fold(lambda x, y: x + y) is None
        True
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
        [Consume]

        Applies a function to each element of the iterable, passing the value on.
        Useful for debugging and inspecting the values in an iterator chain.

        Lazy: func is only called when the returned iterator is consumed, and it
        receives the real elements, not copies.

        >>> rter([1, 2, 3]).map(lambda x: x * 2).inspect(lambda x: print(f"Value: {x}")).collect()
        Value: 2
        Value: 4
        Value: 6
        [2, 4, 6]
        """

        def inner():
            for x in self.iterator:
                func(x)
                yield x

        return IterableWrapper(inner())

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

        >>> counter = iter([10, 20, 30])
        >>> rter([1, 2, 3, 4]).intersperse_with(lambda: next(counter)).collect()
        [1, 10, 2, 20, 3, 30, 4]
        >>> calls = []
        >>> rter([]).intersperse_with(lambda: calls.append(1)).collect()
        []
        >>> rter([1]).intersperse_with(lambda: calls.append(1)).collect()
        [1]
        >>> calls
        []
        """

        def inner():
            first = True
            for x in self.iterator:
                if not first:
                    yield func()
                first = False
                yield x

        return IterableWrapper(inner())

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

        >>> rter([1, 2, 3]).is_sorted_by(lambda x, y: x <= y)
        True
        >>> rter([3, 1, 2]).is_sorted_by(lambda x, y: x <= y)
        False
        """
        it1, it2 = itertools.tee(self.iterator)
        next(it2, None)
        return all(func(a, b) for a, b in zip(it1, it2))

    def is_sorted_by_key(self, f: Callable):
        """
        [Consume]

        Checks if the elements of this iterator are sorted using the given key extraction function.

        Instead of comparing the iterator’s elements directly, this function compares the keys of the elements, as determined by f. Each key is computed exactly once.

        >>> rter(["aaa", "ccc", "bbbbb"]).is_sorted_by_key(len)
        True
        """
        return self.map(f).is_sorted()

    def last(self) -> Optional[T]:
        """
        [Consume]

        Returns the last element.

        >>> rter([1, 2, 3]).last()
        3
        >>> rter([]).last()
        """
        return next(iter(deque(self.iterator, maxlen=1)), None)

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

    def map_windows(self, n, func: Callable[[List[T]], U]):
        """
        [Consume]

        Calls the given function f for each contiguous window of size N over self and returns an iterator over the outputs of f.

        Yields nothing if the iterator has fewer than n elements. n must be at least 1 (Rust panics on n == 0; this library raises ValueError, same policy as step_by).

        Example:
        >>> rter(['a', 'b', 'c', 'd']).map_windows(2, lambda x: ''.join(x)).collect()
        ['ab', 'bc', 'cd']
        >>> rter([1, 2, 3, 4, 5]).map_windows(3, lambda x: sum(x)).collect()
        [6, 9, 12]
        >>> rter([1, 2]).map_windows(3, sum).collect()
        []
        >>> rter([1, 2]).map_windows(0, sum)
        Traceback (most recent call last):
            ...
        ValueError: map_windows() requires n >= 1
        """
        if n < 1:
            raise ValueError("map_windows() requires n >= 1")

        def inner():
            it = iter(self.iterator)
            window = deque(islice(it, n), maxlen=n)
            if len(window) < n:
                return
            yield func(list(window))
            for item in it:
                window.append(item)
                yield func(list(window))

        return IterableWrapper(inner())

    def merge(self, other: Iterable[Any]) -> "IterableWrapper[Any]":
        """
        [Consume]

        Merges two sorted iterators into a single sorted iterator (heapq.merge).

        >>> rter([1, 3, 5]).merge(rter([2, 4, 6])).collect()
        [1, 2, 3, 4, 5, 6]
        >>> rter([1, 2]).merge([3, 4]).collect()
        [1, 2, 3, 4]
        """
        return IterableWrapper(heapq.merge(self.iterator, other))

    def merge_by(self, other: Iterable[Any], less: Callable[[T, T], bool]) -> "IterableWrapper[Any]":
        """
        [Consume]

        Merges two iterators sorted by the given comparison into a single iterator.

        `less(a, b)` returns True when `a` should be placed before `b`.

        >>> rter([5, 3, 1]).merge_by(rter([6, 4, 2]), lambda a, b: a > b).collect()
        [6, 5, 4, 3, 2, 1]
        >>> rter([1, 3]).merge_by(rter([2]), lambda a, b: a < b).collect()
        [1, 2, 3]
        """

        def cmp(a, b):
            if less(a, b):
                return -1
            if less(b, a):
                return 1
            return 0

        return IterableWrapper(heapq.merge(self.iterator, other, key=cmp_to_key(cmp)))

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

    def max_by(self, f: Callable[[T, T], bool]):
        """
        [Consume]

        Returns the element that gives the maximum value with respect to the specified comparison.

        `f(a, b)` returns True when `a` compares greater than or equal to `b`.
        If several elements are equally maximum, the last one is returned, matching Rust.

        >>> rter([1, 2, 3, 2]).max_by(lambda a, b: a >= b)
        3
        >>> rter(["aa", "bb", "cc"]).max_by(lambda a, b: len(a) >= len(b))
        'cc'
        """
        best = None
        first = True
        for item in self.iterator:
            if first or f(item, best):
                best = item
                first = False
        return best

    def max_by_key(self, func: Callable[[T], Any]):
        """
        [Consume]

        Returning the maximum element by mapping the key using the given function.

        If several elements are equally maximum, the first one is returned
        (unlike Rust's `max_by_key`, which returns the last).

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

    def min_by(self, f: Callable[[T, T], bool]):
        """
        [Consume]

        Returns the element that gives the minimum value with respect to the specified comparison.

        `f(a, b)` returns True when `a` compares less than or equal to `b`.
        If several elements are equally minimum, the last one is returned, matching Rust.

        >>> rter([3, 1, 2, 1]).min_by(lambda a, b: a <= b)
        1
        >>> rter(["aa", "b", "c"]).min_by(lambda a, b: len(a) <= len(b))
        'c'
        """
        best = None
        first = True
        for item in self.iterator:
            if first or f(item, best):
                best = item
                first = False
        return best

    def min_by_key(self, func: Callable[[T], Any]):
        """
        [Consume]

        Returning the minimum element by mapping the key using the given function.

        If several elements are equally minimum, the first one is returned
        (unlike Rust's `min_by_key`, which returns the last).

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

    def next_chunk(self, n: int) -> List[T]:
        """
        [Mut ; retains = the rest elements after the chunk]

        Returns the next n elements of the iterator as a list.

        Fewer than n elements are returned if the iterator runs out first.
        Raises ValueError if n is less than 1.

        >>> a = rter(range(6))
        >>> a.next_chunk(2)
        [0, 1]
        >>> a.next_chunk(2)
        [2, 3]
        >>> a.next_chunk(10)
        [4, 5]
        >>> rter([1]).next_chunk(0)
        Traceback (most recent call last):
            ...
        ValueError: n must be at least 1
        """
        if n < 1:
            raise ValueError("n must be at least 1")
        return list(islice(self.iterator, n))

    def nth(self, n: int) -> Optional[T]:
        """
        [Mut ; retains = the rest elements after the specified index]

        Returns the nth element of the iterable.

        Negative n raises ValueError (Rust panics).

        >>> rter([1, 2, 3, 4]).nth(2)
        3
        >>> rter("hello").nth(1)
        'e'
        >>> rter([1, 2]).nth(-1)
        Traceback (most recent call last):
            ...
        ValueError: Indices for islice() must be None or an integer: 0 <= x <= sys.maxsize.
        """
        return next(islice(self.iterator, n, n + 1), None)

    def nth_back(self, n: int) -> Optional[T]:
        """
        [Consume]

        Returns the nth element from the end of the iterator, advancing the iterator past it.

        Returns None if the iterator has fewer than n + 1 elements, in which case the
        remaining elements are kept in self.

        Python iterators cannot go backwards, so the iterator is materialized first;
        the elements before the taken one are kept in self.

        >>> a = rter([1, 2, 3, 4])
        >>> a.nth_back(1)
        3
        >>> a.collect()
        [1, 2]
        >>> rter([1, 2]).nth_back(5) is None
        True
        """
        items = list(self.iterator)
        if n < 0 or n >= len(items):
            self.iterator = iter(items)
            return None
        value = items[len(items) - 1 - n]
        self.iterator = iter(items[: len(items) - 1 - n])
        return value

    @staticmethod
    def once(x: T):
        """
        Returns an iterator of exactly one element.

        >>> rter.once(1).collect()
        [1]
        """
        return IterableWrapper(iter([x]))

    def partial_cmp(self, other):
        """
        [UnMut]

        Lexicographically compares the elements of two iterators, allowing for incomparable elements.

        Returns -1, 0 or 1 as this iterator is less than, equal to, or greater than `other`;
        returns None when a pair of elements is incomparable (neither `a == b`, `a < b`
        nor `a > b` holds). A length mismatch is decided by the common prefix.

        >>> rter([1, 2]).partial_cmp(rter([1, 3]))
        -1
        >>> rter([1, 2]).partial_cmp(rter([1, 2]))
        0
        >>> print(rter([1.0, float("nan")]).partial_cmp(rter([1.0, 2.0])))
        None
        """
        y = other if isinstance(other, IterableWrapper) else IterableWrapper(other)
        x, y = self.clone(), y.clone()
        exhausted = object()
        while True:
            a = next(x, exhausted)
            b = next(y, exhausted)
            if a is exhausted or b is exhausted:
                return (b is exhausted) - (a is exhausted)
            if a == b:
                continue
            if a < b:
                return -1
            if a > b:
                return 1
            return None

    def partial_cmp_by(self, other, func: Callable[[T, T], Optional[int]]):
        """
        [UnMut]

        Lexicographically compares the elements of two iterators with the given partial comparator.

        `func(a, b)` returns -1, 0 or 1 to order the pair, or None if the pair is
        incomparable; an incomparable pair makes the whole comparison return None.

        >>> rter([1, 2]).partial_cmp_by(rter([1, 3]), lambda a, b: (a > b) - (a < b))
        -1
        >>> def mixed(a, b):
        ...     if isinstance(a, str) != isinstance(b, str):
        ...         return None
        ...     return (a > b) - (a < b)
        >>> print(rter([1, 2]).partial_cmp_by(rter([1, "x"]), mixed))
        None
        """
        y = other if isinstance(other, IterableWrapper) else IterableWrapper(other)
        x, y = self.clone(), y.clone()
        exhausted = object()
        while True:
            a = next(x, exhausted)
            b = next(y, exhausted)
            if a is exhausted or b is exhausted:
                return (b is exhausted) - (a is exhausted)
            ordering = func(a, b)
            if ordering is None:
                return None
            if ordering != 0:
                return ordering

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

    def peekable(self) -> "Peekable[T]":
        """
        [Consume]

        Turns the iterator into a peekable one, adding a peek() method with single-element lookahead.

        peek() does not consume the peeked element; the iteration order is unaffected by peeking.

        >>> a = rter([1, 2, 3]).peekable()
        >>> a.peek()
        1
        >>> a.peek()
        1
        >>> a.collect()
        [1, 2, 3]
        >>> b = rter([]).peekable()
        >>> print(b.peek())
        None
        >>> b.peek(-1)
        -1
        >>> list(b)
        []
        """
        return Peekable(self.iterator)

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
        >>> rter([2, 3]).product(2)
        12
        >>> rter([]).product()
        1
        """
        if initial is None:
            return math.prod(self.iterator)
        return math.prod(self.iterator, start=initial)

    def reduce(self, func: Callable[[T, T], T], initial: Any = _SENTINEL):
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
        >>> rter([]).reduce(lambda x, y: x + y) is None
        True
        """
        if initial is not _SENTINEL:
            return reduce(func, self.iterator, initial)
        for first in self.iterator:
            acc = first
            break
        else:
            return None
        for item in self.iterator:
            acc = func(acc, item)
        return acc

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

    def rfind(self, predicate: Callable[[T], bool]) -> Optional[T]:
        """
        [Consume]

        Searches for an element from the end, returning it.

        Returns None if no element satisfies the predicate, in which case self is
        left empty. Python iterators cannot go backwards, so the iterator is
        materialized first; the elements before the found one are kept in self.

        >>> a = rter([1, 2, 3, 4])
        >>> a.rfind(lambda x: x % 2 == 0)
        4
        >>> a.collect()
        [1, 2, 3]
        >>> rter([1, 3]).rfind(lambda x: x % 2 == 0) is None
        True
        """
        items = list(self.iterator)
        for i in range(len(items) - 1, -1, -1):
            if predicate(items[i]):
                self.iterator = iter(items[:i])
                return items[i]
        return None

    def rfold(self, func: Callable[[Any, T], Any], initial):
        """
        [Consume]

        Folds the elements from the end, by repeatedly applying a reducing operation.

        Python iterators cannot go backwards, so the iterator is materialized first.

        >>> rter(["a", "b", "c"]).rfold(lambda acc, x: acc + x, "")
        'cba'
        >>> rter([]).rfold(lambda acc, x: acc + x, 0)
        0
        """
        acc = initial
        for item in reversed(list(self.iterator)):
            acc = func(acc, item)
        return acc

    def rposition(self, predicate):
        """
        [Consume]

        Searches for an element in an iterator from the end, returning its index.

        >>> rter([1, 2, 3, 4]).rposition(lambda x: x == 2)
        1
        >>> rter([1, 2, 3]).rposition(lambda x: x % 5 == 0)
        """
        items = list(self.iterator)
        for i in range(len(items) - 1, -1, -1):
            if predicate(items[i]):
                return i

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

    def scan(self, initial: S, func: Callable[[S, T], Optional[Tuple[S, U]]]) -> "IterableWrapper[U]":
        """
        [Consume]

        A fold-like adapter that holds internal state and yields items derived from it.

        `func(state, x)` is called with the current state and each element x.
        If it returns a `(new_state, item)` tuple, `item` is yielded and iteration
        continues with `new_state`; if it returns None, the iteration terminates early.

        >>> rter([1, 2, 3, 4]).scan(0, lambda s, x: (s + x, s + x)).collect()
        [1, 3, 6, 10]
        >>> rter([1, 2, 3, 4]).scan(0, lambda s, x: None if s + x > 3 else (s + x, s + x)).collect()
        [1, 3]
        """

        def inner():
            state = initial
            for item in self.iterator:
                result = func(state, item)
                if result is None:
                    return
                state, value = result
                yield value

        return IterableWrapper(inner())
    def size_hint(self) -> int:
        """
        [UnMut]

        Returns a lower bound of the remaining length of the iterator (operator.length_hint).

        The hint is exact whenever the underlying iterator exposes its remaining
        length; otherwise 0 is returned.

        >>> a = rter([1, 2, 3])
        >>> a.size_hint()
        3
        >>> a.next()
        1
        >>> a.size_hint()
        2
        >>> rter(map(abs, [1, 2, 3])).size_hint()
        0
        """
        return length_hint(self.iterator)

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
        >>> rter([None, 2]).skip_while(lambda x: False).collect()
        [None, 2]
        """
        try:
            n = next(self.iterator)
            while predicate(n):
                n = next(self.iterator)
        except StopIteration:
            return IterableWrapper.empty()
        # n survived StopIteration, so it is a real element (possibly None).
        return IterableWrapper.once(n).chain(self)

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

        step < 1 raises ValueError (Rust panics on step == 0).

        >>> rter([1, 2, 3, 4, 5, 6]).step_by(2).collect()
        [1, 3, 5]
        >>> rter("hello").step_by(3).collect()
        ['h', 'l']
        >>> rter([1, 2]).step_by(0)
        Traceback (most recent call last):
            ...
        ValueError: Step for islice() must be a positive integer or None.
        """
        return IterableWrapper(islice(self.iterator, 0, None, step))

    def sum(self):
        """
        [Consume]

        Sums the elements of an iterator.

        >>> rter([1, 2, 3]).sum()
        6
        >>> rter([]).sum()
        0
        """
        return sum(self.iterator)

    def take(self, n: int):
        """
        [Consume]

        Take the first `n` elements from the iterable.

        Returns a lazy view: the source iterator is advanced only as the view is consumed, matching Rust's lazy `take` (earlier releases eagerly drained the first `n` elements on call).

        >>> rter([1, 3, 2, 4]).take(3).collect()
        [1, 3, 2]
        >>> rter([1, 2]).take(-1)
        Traceback (most recent call last):
            ...
        ValueError: Stop argument for islice() must be None or an integer: 0 <= x <= sys.maxsize.
        """
        return IterableWrapper(islice(self.iterator, n))

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

    def try_collect(self, container: Union[Callable[[Iterable[Any]], Any], type] = list, catch: type = Exception):
        """
        [Mut]

        A variant of collect that stops and returns the raised exception instead of propagating it.

        If consuming the iterator raises an exception matching `catch`, iteration stops
        immediately and the exception instance is returned; otherwise the collected
        container is returned.

        >>> rter([1, 2, 3]).try_collect()
        [1, 2, 3]
        >>> rter([1, 2, 3]).try_collect(set)
        {1, 2, 3}
        >>> def failing():
        ...     yield 1
        ...     raise ValueError("boom")
        >>> err = rter(failing()).try_collect(catch=ValueError)
        >>> isinstance(err, ValueError)
        True
        """
        try:
            return container(self.iterator)
        except catch as e:
            return e

    def try_find(self, predicate: Callable[[T], bool], catch: type = Exception):
        """
        [Mut ; retains = the rest elements after the found one or the raised error]

        A variant of find that stops and returns the raised exception instead of propagating it.

        If `predicate` raises an exception matching `catch`, iteration stops immediately
        and the exception instance is returned; otherwise the first matching element
        (or None) is returned.

        >>> rter([1, 2, 3]).try_find(lambda x: x > 1)
        2
        >>> rter([1, 2, 3]).try_find(lambda x: x > 5)
        >>> err = rter([1, "a", 2]).try_find(lambda x: x > 1)
        >>> isinstance(err, TypeError)
        True
        """
        for item in self.iterator:
            try:
                if predicate(item):
                    return item
            except catch as e:
                return e

    def try_fold(self, initial: S, func: Callable[[S, T], S], catch: type = Exception):
        """
        [Mut]

        A variant of fold that stops and returns the raised exception instead of propagating it.

        If `func` raises an exception matching `catch`, iteration stops immediately and
        the exception instance is returned; otherwise the folded value is returned.

        >>> rter([1, 2, 3]).try_fold(0, lambda acc, x: acc + x)
        6
        >>> err = rter([1, 0, 2]).try_fold(0, lambda acc, x: acc + 10 // x)
        >>> isinstance(err, ZeroDivisionError)
        True
        """
        acc = initial
        for item in self.iterator:
            try:
                acc = func(acc, item)
            except catch as e:
                return e
        return acc

    def try_for_each(self, func: Callable[[T], Any], catch: type = Exception):
        """
        [Mut]

        A variant of for_each that stops and returns the raised exception instead of propagating it.

        >>> rter([1, 2]).try_for_each(print)
        1
        2
        >>> err = rter(["1", "x", "2"]).try_for_each(int, catch=ValueError)
        >>> isinstance(err, ValueError)
        True
        """
        for item in self.iterator:
            try:
                func(item)
            except catch as e:
                return e

    def try_reduce(self, func: Callable[[T, T], T], catch: type = Exception):
        """
        [Mut]

        A variant of reduce that stops and returns the raised exception instead of propagating it.

        Returns None if the iterator is empty.

        >>> rter([1, 2, 3]).try_reduce(lambda a, b: a + b)
        6
        >>> rter([]).try_reduce(lambda a, b: a + b)
        >>> err = rter([1, 0, 2]).try_reduce(lambda a, b: a + 10 // b)
        >>> isinstance(err, ZeroDivisionError)
        True
        """
        acc = None
        first = True
        for item in self.iterator:
            try:
                if first:
                    acc = item
                    first = False
                else:
                    acc = func(acc, item)
            except catch as e:
                return e
        return acc

    def unique(self) -> "IterableWrapper[T]":
        """
        [Consume]

        Removes duplicate elements, keeping the first occurrence of each.

        >>> rter([1, 2, 1, 3, 2]).unique().collect()
        [1, 2, 3]
        >>> rter("hello").unique().collect()
        ['h', 'e', 'l', 'o']
        """
        return IterableWrapper(dict.fromkeys(self.iterator))

    def unzip(self):
        """
        [Consume]

        Converts an iterator of pairs into a pair of containers.

        >>> a, b = rter([(1, 'a'), (2, 'b'), (3, 'c')]).unzip()
        >>> list(a)
        [1, 2, 3]
        >>> list(b)
        ['a', 'b', 'c']
        >>> rter([]).unzip()
        ([], [])
        """
        left: List[Any] = []
        right: List[Any] = []
        for a, b in self.iterator:
            left.append(a)
            right.append(b)
        return left, right

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

    def __repr__(self):
        """
        >>> rter([1, 2])
        <rter list_iterator>
        >>> rter(x for x in [1, 2])
        <rter generator>
        """
        return f"<rter {type(self.iterator).__name__}>"

    def _compare(self, other: Any):
        """
        [UnMut]

        Helper function to compare two iterators lexicographically.

        Accepts any iterable (wrapped on the fly) and returns NotImplemented
        for non-iterables.

        returns 1 if a > b, -1 if a < b, 0 if equal
        """
        if not isinstance(other, IterableWrapper):
            if not isinstance(other, Iterable):
                return NotImplemented
            other = IterableWrapper(other)

        x, y = self.clone(), other.clone()

        while True:
            a, b = next(x, _SENTINEL), next(y, _SENTINEL)
            if a is _SENTINEL or b is _SENTINEL:
                return (b is _SENTINEL) - (a is _SENTINEL)
            if a != b:
                return (a > b) - (a < b)  # type: ignore

    def __eq__(self, other):
        c = self._compare(other)
        if c is NotImplemented:
            return NotImplemented
        return c == 0

    def __lt__(self, other):
        c = self._compare(other)
        if c is NotImplemented:
            return NotImplemented
        return c < 0

    def __le__(self, other):
        c = self._compare(other)
        if c is NotImplemented:
            return NotImplemented
        return c <= 0

    def __gt__(self, other):
        c = self._compare(other)
        if c is NotImplemented:
            return NotImplemented
        return c > 0

    def __ge__(self, other):
        c = self._compare(other)
        if c is NotImplemented:
            return NotImplemented
        return c >= 0


class Peekable(IterableWrapper[T]):
    """
    An IterableWrapper with single-element lookahead.

    peek() returns the next element without consuming it, so the iteration
    order is unaffected by peeking.
    """

    __slots__ = ("_buffer",)

    def __init__(self, iterable: Iterable[T]):
        self._buffer: List[T] = []
        super().__init__(self._stream(iter(iterable)))

    def _stream(self, source: Iterator[T]) -> Iterator[T]:
        while True:
            if self._buffer:
                yield self._buffer.pop(0)
            else:
                try:
                    yield next(source)
                except StopIteration:
                    return

    def peek(self, default=None) -> Optional[T]:
        """
        [UnMut]

        Returns the next element without consuming it.

        If the iterator is exhausted, returns default and consumes nothing.

        >>> a = rter([1, 2]).peekable()
        >>> a.peek()
        1
        >>> a.next()
        1
        >>> a.peek()
        2
        """
        if not self._buffer:
            try:
                self._buffer.append(next(self.iterator))
            except StopIteration:
                return default
        return self._buffer[0]


rter = IterableWrapper


def from_fn(func: Callable[[], Optional[T]]) -> IterableWrapper[T]:
    """
    Creates a new iterator where each element is produced by calling func.

    Iteration stops when func returns None.

    >>> counter = iter(range(3))
    >>> from_fn(lambda: next(counter, None)).collect()
    [0, 1, 2]
    >>> from_fn(lambda: None).collect()
    []
    """

    def inner():
        while True:
            item = func()
            if item is None:
                return
            yield item

    return IterableWrapper(inner())


def once_with(func: Callable[[], T]) -> IterableWrapper[T]:
    """
    Lazily produces exactly one value by calling func.

    func is called only when the value is first requested.

    >>> calls = []
    >>> it = once_with(lambda: calls.append(1) or "value")
    >>> len(calls)
    0
    >>> it.collect()
    ['value']
    >>> len(calls)
    1
    """

    def inner():
        yield func()

    return IterableWrapper(inner())


def repeat_n(x: T, n: int) -> IterableWrapper[T]:
    """
    Creates an iterator that repeats x exactly n times.

    Alias of `repeat`, named after Rust 1.82 `std::iter::repeat_n`.

    >>> repeat_n(2, 3).collect()
    [2, 2, 2]
    """
    return IterableWrapper.repeat(x, n)


def successors(initial: Optional[T], succ: Callable[[T], Optional[T]]) -> IterableWrapper[T]:
    """
    Creates a new iterator that yields initial and then elements generated by succ.

    succ(x) returns the next element, or None to stop the iteration.

    >>> successors(3, lambda x: x - 1 if x > 0 else None).collect()
    [3, 2, 1, 0]
    >>> successors(None, lambda x: x).collect()
    []
    >>> successors((0, 1), lambda p: (p[1], p[0] + p[1])).map(lambda p: p[0]).take(8).collect()
    [0, 1, 1, 2, 3, 5, 8, 13]
    """

    def inner():
        current = initial
        while current is not None:
            yield current
            current = succ(current)

    return IterableWrapper(inner())

if __name__ == "__main__":
    import doctest

    doctest.testmod()
