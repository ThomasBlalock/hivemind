def count_vowels(s: str) -> int:
    """Count the number of vowels (a, e, i, o, u) in a string, case-insensitive."""
    vowels = set("aeiou")
    count = 0
    for ch in s.lower():
        if ch not in vowels:  # BUG: should be `in vowels`
            count += 1
    return count
