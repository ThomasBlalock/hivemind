---
id: regex-construction
title: Construct and test regular expressions safely
description: When the user needs a regex, build it incrementally, test it against examples first, and prefer non-regex solutions when possible.
triggers: ["regex", "regular expression", "pattern match", "re.match", "re.search"]
source: hivemind/toy@v0
---

# Regex construction playbook

## Decide if regex is the right tool

- For fixed-string search: use `str.find` / `in` / `str.startswith`. Faster, clearer.
- For structured data (JSON, HTML, YAML): use the proper parser. Regex on HTML is a meme for a reason.
- For tokenizing/parsing complex grammars: use a real parser (`lark`, `pyparsing`). Regexes accumulate edge cases until they collapse.

## If regex really is the right tool

1. Write 3–5 example strings that **should** match and 3–5 that **should not** match. Put them in a test before writing the pattern.
2. Build the pattern from left to right, character-class by character-class. After each addition, re-run the tests.
3. Use `re.VERBOSE` to write multi-line regexes with comments — much easier to read in PRs:

```python
PATTERN = re.compile(r"""
    ^(?P<year>\d{4})       # year
    -(?P<month>\d{2})      # month
    -(?P<day>\d{2})$       # day
""", re.VERBOSE)
```

4. Use named groups (`(?P<name>...)`) instead of positional indices. Future you will thank present you.
5. For anchors, prefer `^` and `$` over `\A` and `\Z` unless you specifically need MULTILINE semantics.

## Performance traps

- Catastrophic backtracking: avoid nested quantifiers like `(a+)+`. If the input is adversarial, use `regex` library (supports atomic groups) or rewrite the pattern.
- Compile once: `_PATTERN = re.compile(...)` at module level, not inside a hot loop.
