from repeats import find_repeated_words


def test_simple_duplicate():
    assert find_repeated_words("the the cat") == ["the"]


def test_no_duplicates():
    assert find_repeated_words("the quick brown fox") == []


def test_case_insensitive():
    assert find_repeated_words("The the cat") == ["the"]


def test_multiple_duplicates():
    assert find_repeated_words("buffalo buffalo bison bison") == ["buffalo", "bison"]
