# Eval tasks

Self-contained bug-fix tasks for the harness sweep. Each task lives at
`eval_tasks/<id>/` with:

- `task.yaml` — `id`, `prompt`, `test_cmd`, optional `setup_cmd`.
- `repo/` — the buggy code plus pytest tests. The harness `cd`s into here.

The success signal is the test command's exit code. Tasks should be solvable
in fewer than ~10 agent turns. Prompts are written naturally and do **not**
mention skill names from the corpus — the retrieval system has to find
relevant skills on its own.

## Catalog

### Easy
| Id | Bug |
|---|---|
| `fizzbuzz_off_by_one` | Off-by-one in a `range()` call |
| `regex_backref` | Wrong regex backreference syntax |
| `count_vowels_wrong_op` | Inverted membership check (`not in` vs `in`) |
| `missing_return_factorial` | Missing `return` keyword on recursive branch |
| `negative_indices_clamp` | Missing lower-bound check (negative indices wrap) |
| `strip_only_trailing` | Used `.strip()` instead of `.rstrip()` |

### Medium
| Id | Bug |
|---|---|
| `sort_by_length_stable` | Hash-based tiebreak destroys stable sort order |
| `dict_default_mutability` | Mutable default argument shared across calls |
| `parse_int_overflow` | Missing range bounds check on parsed int |
| `group_by_keyfn` | Used `set` instead of `list` for group members |

### Harder
| Id | Bug |
|---|---|
| `sliding_window_avg` | O(n*k) implementation; needs O(n) prefix-sum refactor and edge-case guards |
| `context_manager_leak` | `__exit__` short-circuits on the exception path; file handle leaks |
| `priority_queue_tiebreak` | Heap entries don't include an insertion counter, breaking FIFO ties and crashing on unorderable items |
| `memoize_unhashable` | Cache key build raises TypeError for unhashable args |

## Authoring a new task

1. Make `eval_tasks/<id>/repo/` with the buggy module and a pytest file.
2. Write `eval_tasks/<id>/task.yaml` with the natural-language prompt (do not
   leak any skill names from the corpus).
3. Verify the bug actually fails — `tests/test_eval_tasks.py` enforces this
   automatically by running every task's `test_cmd` and asserting it exits
   non-zero. That catches the "I forgot to introduce the bug" mistake.
