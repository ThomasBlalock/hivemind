import os
import tempfile

import pytest

from safe_writer import SafeWriter


def test_closes_on_success():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "ok.txt")
        with SafeWriter(p) as w:
            w.write("hello")
        # File should be readable and contain "hello"; if the handle weren't
        # closed, the OS would still hold the buffer.
        with open(p) as f:
            assert f.read() == "hello"


def test_closes_on_exception():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "err.txt")
        with pytest.raises(RuntimeError):
            with SafeWriter(p) as w:
                w.write("partial")
                raise RuntimeError("boom")
        # File handle is closed → reading the file works without resource warnings.
        with open(p) as f:
            assert "partial" in f.read()


def test_close_idempotent():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "x.txt")
        sw = SafeWriter(p)
        with sw:
            sw.write("a")
        # _f should be cleared so a stray reference can be GC'd cleanly.
        assert sw._f is None
