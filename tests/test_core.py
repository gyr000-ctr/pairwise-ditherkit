import math
import struct
import threading
import zlib

import pytest

import ditherkit

def _raises(fn, exc=ValueError):
    try:
        fn()
    except exc:
        return True
    return False

def _img(n=8):
    return [[0.5] * 4 for _ in range(n)]


def _whole(seed, rows, levels=2):
    s = ditherkit.DitherSession(seed)
    s.quantize_rows(rows, levels)
    return s.flush()


def _chunked(seed, rows, levels=2):
    s = ditherkit.DitherSession(seed)
    for row in rows:
        s.quantize_rows([row], levels)
    return s.flush()


def _same_seed():
    a = _whole(7, _img())
    b = _whole(7, _img())
    return a == b


def _chunk_equals_whole():
    rows = _img(6)
    return _chunked(3, rows) == _whole(3, rows)


def _diff_seed():
    return _whole(1, _img(6)) != _whole(2, _img(6))


def _reset_reproduces():
    s = ditherkit.DitherSession(5)
    s.quantize_rows(_img(4))
    a = s.flush()
    s.reset(5)
    s.quantize_rows(_img(4))
    return s.flush() == a


def _state_bounded():
    s = ditherkit.DitherSession(1)
    s.quantize_rows(_img(4))
    a = s.state_size()
    s.quantize_rows(_img(400))
    return s.state_size() == a


def _levels():
    return _raises(lambda: _whole(1, _img(2), levels=1))


def _range():
    return _raises(lambda: _whole(1, [[1.5] * 4], levels=2))


def _values():
    out = _whole(1, _img(4))
    return all(v in (0, 1) for row in out for v in row)


def _empty():
    return _whole(0, []) == []


def _flush_idempotent():
    s = ditherkit.DitherSession(1)
    s.quantize_rows(_img(2))
    a = s.flush()
    return s.flush() == a


def _white():
    out = _whole(1, [[1.0] * 4 for _ in range(4)])
    return all(v == 1 for row in out for v in row)


def _black():
    out = _whole(1, [[0.0] * 4 for _ in range(4)])
    return all(v == 0 for row in out for v in row)


def _row_len():
    out = _whole(1, [[0.5] * 4])
    return len(out) == 1 and len(out[0]) == 4

CASES = [
        ("same_seed", lambda: _same_seed()),
        ("chunk_equals_whole", lambda: _chunk_equals_whole()),
        ("diff_seed", lambda: _diff_seed()),
        ("reset", lambda: _reset_reproduces()),
        ("state_bounded", lambda: _state_bounded()),
        ("levels", lambda: _levels()),
        ("range", lambda: _range()),
        ("values", lambda: _values()),
        ("empty", lambda: _empty()),
        ("flush_idempotent", lambda: _flush_idempotent()),
        ("white", lambda: _white()),
        ("black", lambda: _black()),
        ("row_len", lambda: _row_len()),
        ("two_sessions", lambda: _whole(9, _img(5)) == _whole(9, _img(5))),
        ("reset_seed_change", lambda: _whole(1, _img(5)) != _whole(2, _img(5))),
    ]


@pytest.mark.parametrize("name,check", CASES, ids=[c[0] for c in CASES])
def test_spec(name, check):
    assert check() is True
