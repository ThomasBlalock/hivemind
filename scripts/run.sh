#!/bin/bash
# Eval sweep — hardest tier only, cheap models.
#
# Each (model × policy) cell runs in its own fresh repo copy — earlier
# versions shared one repo per (run × task), so the first cell's fix leaked
# into every subsequent pytest run and forced 100% across the board.

.venv/bin/python scripts/run_harness_sweep.py \
    --models 'openrouter/tencent/hy3-preview' 'openrouter/deepseek/deepseek-v4-flash' \
    --policies baseline_a baseline_b hybrid_retrieval \
    --tasks eval_tasks/sliding_window_avg \
            eval_tasks/context_manager_leak \
            eval_tasks/priority_queue_tiebreak \
            eval_tasks/memoize_unhashable \
    --runs 2 \
    --out runs/sweep_first_live.csv

.venv/bin/python scripts/build_report.py runs/sweep_first_live.csv
