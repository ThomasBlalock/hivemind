#!/bin/bash

python scripts/run_harness_sweep.py \
    --models 'openrouter/anthropic/claude-haiku-4.5' 'openrouter/anthropic/claude-sonnet-4.6' \
    --policies baseline_a baseline_b hybrid_retrieval \
    --tasks eval_tasks/fizzbuzz_off_by_one eval_tasks/regex_backref \
            eval_tasks/dict_default_mutability eval_tasks/missing_return_factorial \
    --runs 2 \
    --out runs/sweep_first_live.csv

python scripts/build_report.py runs/sweep_first_live.csv