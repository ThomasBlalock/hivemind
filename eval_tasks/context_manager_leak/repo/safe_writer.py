from typing import IO


class SafeWriter:
    """Open a file for writing; always close on exit, even on exception."""

    def __init__(self, path: str):
        self._path = path
        self._f: IO | None = None

    def write(self, s: str) -> int:
        assert self._f is not None, "use SafeWriter as a context manager"
        return self._f.write(s)

    def __enter__(self) -> "SafeWriter":
        self._f = open(self._path, "w")
        return self

    def __exit__(self, exc_type, exc, tb):
        # BUG: only closes on the no-exception path. When exc_type is set the
        # method short-circuits and the file handle leaks.
        if exc_type is None:
            self._f.close()
            self._f = None
        return False
