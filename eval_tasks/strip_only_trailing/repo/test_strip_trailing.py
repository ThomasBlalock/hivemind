from strip_trailing import strip_trailing_whitespace


def test_preserves_indentation():
    src = "    def foo():   \n        return 1   \n"
    expected = "    def foo():\n        return 1\n"
    assert strip_trailing_whitespace(src) == expected


def test_no_change_when_clean():
    src = "hello\nworld\n"
    assert strip_trailing_whitespace(src) == src


def test_no_final_newline_preserved():
    src = "alpha   "
    assert strip_trailing_whitespace(src) == "alpha"
