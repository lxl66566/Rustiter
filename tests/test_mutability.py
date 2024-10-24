from rustiter import rter


def test_all_mut():
    a = rter([1, 2, 3])
    _ = a.all(lambda x: x > 2)
    assert a.ne(rter([1, 2, 3]))


def test_any_mut():
    a = rter([1, 2, 3])
    _ = a.any(lambda x: x > 2)
    assert a.ne(rter([1, 2, 3]))


def test_clone_unmut():
    a = rter([1, 2, 3])
    _ = a.clone().collect()
    assert a.eq(rter([1, 2, 3]))


def test_cloned_unmut():
    a = rter([1, 2, 3])
    _ = a.cloned().collect()
    assert a.eq(rter([1, 2, 3]))


def test_enumerate_consume():
    a = rter([1, 2, 3])
    _ = a.enumerate().collect()
    assert a.is_empty()


def test_filter_consume():
    a = rter([1, 2, 3])
    _ = a.filter(lambda x: x > 2).collect()
    assert a.is_empty()


def test_fuse_mut():
    a = rter([1, 2, None, 3, 4])
    _ = a.fuse().collect()
    assert a.eq(rter([3, 4]))


def test_intersperse_consume():
    a = rter([1, 2, 3, 4])
    _ = a.intersperse(0).collect()
    assert a.is_empty()


def test_is_empty_unmut():
    a = rter([1, 2, 3])
    _ = a.is_empty()
    assert a.eq(rter([1, 2, 3]))


def test_is_partitioned_unmut():
    a = rter([1, 2, 3])
    _ = a.is_partitioned(lambda x: x <= 1)
    assert a.is_empty()


def test_map_consume():
    a = rter([1, 2, 3, 4])
    _ = a.map(lambda x: x * 2).collect()
    assert a.is_empty()


def test_next_mut():
    a = rter([1, 2, 3])
    _ = a.next()
    assert a.eq(rter([2, 3]))


def test_nth_mut():
    a = rter([1, 2, 3])
    _ = a.nth(1)
    assert a.eq(rter([3]))


def test_position_mut():
    a = rter([1, 2, 3])
    _ = a.position(lambda x: x == 1)
    assert a.eq(rter([2, 3]))


def test_sorted_consume():
    a = rter([1, 3, 2])
    _ = a.sorted().collect()
    assert a.is_empty()


def test_skip_consume():
    a = rter([1, 2, 3])
    _ = a.skip(1).collect()
    assert a.is_empty()


def test_skip_while_consume():
    a = rter([1, 2, 3])
    _ = a.skip_while(lambda x: x < 2).collect()
    assert a.is_empty()


def test_take_mut():
    a = rter([1, 2, 3, 4])
    _ = a.take(2).collect()
    assert a.eq(rter([3, 4]))


def test_compares_unmut():
    for func in [rter.ne, rter.eq, rter.lt, rter.le, rter.gt, rter.ge]:
        a = rter([1, 2, 3])
        _ = func(a, rter([1, 2, 3]))
        assert a.eq(rter([1, 2, 3]))
