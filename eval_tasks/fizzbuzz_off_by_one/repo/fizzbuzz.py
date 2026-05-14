def fizzbuzz(n: int) -> list[str]:
    """Return the fizzbuzz sequence for 1..n inclusive.

    Bug: this returns 1..n-1 because the range is exclusive at the wrong end.
    """
    out = []
    for i in range(1, n):  # BUG: should be range(1, n + 1)
        if i % 15 == 0:
            out.append("FizzBuzz")
        elif i % 3 == 0:
            out.append("Fizz")
        elif i % 5 == 0:
            out.append("Buzz")
        else:
            out.append(str(i))
    return out
