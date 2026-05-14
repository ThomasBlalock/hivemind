from vowels import count_vowels


def test_basic():
    assert count_vowels("hello") == 2
    assert count_vowels("world") == 1


def test_empty():
    assert count_vowels("") == 0


def test_case_insensitive():
    assert count_vowels("AEIOU") == 5
