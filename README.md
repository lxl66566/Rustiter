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

## benchmark

Each data is in seconds. You can run [bench.py](./bench.py) manually.

Windows 11, python 3.12.7

| bench | rustiter | builtin |
| ----- | -------- | ------- |
| 1     | 0.21076  | 0.06355 |
