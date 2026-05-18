import re


# Bug: this pattern matches any two adjacent words, not just *equal* adjacent
# words. The fix is a regex backreference: \b(\w+)\s+\1\b
_PATTERN = re.compile(r"\b(\w+)\s+(\w+)\b")


def find_repeated_words(text: str) -> list[str]:
    """Return the list of words that appear twice in a row (case-insensitive).

    Examples:
        >>> find_repeated_words("the the cat")
        ['the']
        >>> find_repeated_words("hello world")
        []
    """
    out = []
    for m in _PATTERN.finditer(text.lower()):
        out.append(m.group(1))
    return out
