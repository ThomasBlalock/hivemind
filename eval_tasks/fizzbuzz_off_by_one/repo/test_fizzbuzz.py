from fizzbuzz import fizzbuzz


def test_fizzbuzz_15_full_sequence():
    expected = [
        "1", "2", "Fizz", "4", "Buzz", "Fizz", "7", "8",
        "Fizz", "Buzz", "11", "Fizz", "13", "14", "FizzBuzz",
    ]
    assert fizzbuzz(15) == expected


def test_fizzbuzz_5():
    assert fizzbuzz(5) == ["1", "2", "Fizz", "4", "Buzz"]
