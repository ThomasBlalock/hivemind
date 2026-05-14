---
id: python-debugging
title: Debug a failing Python test or runtime error
description: When a Python test fails or code raises an exception in a way that isn't obvious from the traceback, use this structured approach instead of guessing.
triggers: ["traceback", "pytest", "AttributeError", "TypeError", "flaky test", "debug python"]
source: hivemind/toy@v0
---

# Python debugging playbook

## First pass (don't skip)

1. Read the **last** frame of the traceback, then read the **first** frame. The last frame is where it broke; the first frame is what the user actually invoked.
2. State out loud (or in your scratchpad) what the exception type literally means. `AttributeError: 'NoneType' object has no attribute 'foo'` means *something that should have been a value is None*.
3. Identify the smallest unit you can run to reproduce. If reproducing requires the whole test suite, fix the reproduction before fixing the bug.

## If the cause isn't obvious

- Add `breakpoint()` (Python 3.7+) at the suspected line and run. Don't reach for IDE debuggers in CI/sandbox environments.
- For pytest: `pytest -x -vv -s path::test_name` — stop on first failure, verbose, no capture.
- For flaky tests: `pytest --count=20 path::test_name` (needs pytest-repeat) and find what changes between passes.
- Print the **type** of suspect values, not just the value: `print(type(x), x)`. Wrong type is a more common bug than wrong value.

## Common patterns

- `AttributeError: 'NoneType' object has no attribute X` → a function returned None implicitly. Trace back to where a return was forgotten.
- `TypeError: argument of type 'X' is not iterable` → a string slipped in where a list/dict was expected (or vice versa).
- `RecursionError` → almost always a missing base case or mutual recursion through a property.

## Anti-patterns

- Wrapping the failing line in `try/except: pass`. This is suppression, not debugging.
- "Restart and see if it's still broken." It is.
