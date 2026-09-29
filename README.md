# Rustiter

Rust-inspired iterator utilities for Python. This library implements **most of** the functions from the [Rust Iterator trait](https://doc.rust-lang.org/std/iter/trait.Iterator.html).

## Why

I'm a big fan of chaining function calls, but Python's functional programming tools can be cumbersome. No one really wants to use the built-in `map`, `filter`, and `reduce` functions.

I previously experimented with [simpleufcs](https://github.com/lxl66566/simpleufcs), which allows for chainable function calls in Python.

This library offers an alternative: while it doesn't provide full UFCS (Uniform Function Call Syntax), it performs slightly better and brings many useful functions from Rust’s iterator design, such as `take`, `flat_map`, and more. If you're familiar with Rust and not too concerned about performance, you'll likely enjoy using this.

## Installation

```sh
pip install rustiter
```

## Example

Here are some commonly used functions:

```py
from rustiter import rter
ret = (
    rter(range(10))
    .filter(lambda x: x % 2 == 0)
    .map(lambda x: x + 1)
    .take(3)
    .collect()
)
assert ret == [1, 3, 5]
assert rter(range(10)).reduce(lambda x, y: x + y, 0) == 45
```

Additional Information: **Every function** includes a doctest to demonstrate its usage.

### Mutability

The mutability of Python's iterator is not ideal. Therefore, I marked the mutability of the functions as follows:

- `[Mut]`: The iterator may be modified after this operation. If there's not a `retains = ...`, the rest elements is undefined.
- `[UnMut]`: The iterator will not be modified.
- `[Consume]`: The iterator may be consumed after this operation. Note that this **does not** mean the iterator will become empty; there may still be elements in it. This means that you should not use this iterator again.

### Differences from Rust

`cloned` / `copied` in this library operate on the **iterator object itself**, not on each element:

- `clone` / `copy` return a tee-based shallow copy of the iterator.
- `cloned` / `deepcopy` return `copy.deepcopy` of the iterator, duplicating its current state.

Rust's `Iterator::cloned` / `Iterator::copied` instead clone/copy **each element** (turning an iterator of references into an iterator of values); there is no per-element copy in this library's methods of the same name.

Because `cloned` / `deepcopy` rely on `copy.deepcopy`, they only work when the internal iterator supports it: C-implemented iterators (`list_iterator`, `map`, `filter`, `enumerate`, ...) are fine, but generator-based iterators (e.g. `rter(x for x in [1, 2])` and chains built on them) raise `TypeError: cannot pickle 'generator' object`.

## benchmark

Windows 11, python 3.12.9

| Name (time in ns) | Min               | Max                 | Mean              | StdDev             | Median            | IQR              | Outliers   | OPS (Kops/s)     | Rounds | Iterations |
| ----------------- | ----------------- | ------------------- | ----------------- | ------------------ | ----------------- | ---------------- | ---------- | ---------------- | ------ | ---------- |
| test_normal       | 475.0000 (1.0)    | 1,935.0002 (1.0)    | 495.1749 (1.0)    | 17.9839 (1.0)      | 494.9998 (1.0)    | 5.0000 (1.0)     | 1423;4186  | 2,019.4886 (1.0) | 98040  | 20         |
| test_rustiter     | 899.9996 (1.89)   | 96,300.0057 (49.77) | 1,068.6410 (2.16) | 422.1214 (23.47)   | 1,100.0011 (2.22) | 100.0008 (20.00) | 156;194    | 935.7689 (0.46)  | 60241  | 1          |
