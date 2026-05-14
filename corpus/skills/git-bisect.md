---
id: git-bisect
title: Use git bisect to find a regression
description: When the user reports a regression with a known good commit and a known bad commit, drive git bisect to find the introducing commit.
triggers: ["bisect", "regression", "broken commit", "find when broke"]
source: hivemind/toy@v0
---

# git bisect playbook

When a user reports a regression and can name a commit where it worked, prefer `git bisect` to manual hunting.

## Procedure

1. Confirm the user has a reliable reproduction script. Bisect is only as good as the test.
2. `git bisect start`
3. `git bisect bad <current_bad_sha>` — usually `HEAD`.
4. `git bisect good <known_good_sha>`.
5. For each commit git checks out, run the reproduction script. Mark `git bisect good` or `git bisect bad`.
6. When git reports the first bad commit, run `git show <sha>` and explain to the user *what changed* in that commit that introduced the regression.
7. `git bisect reset` to return to the original branch.

## Variants

- **Automated**: if the reproduction can be scripted with a 0/non-zero exit, use `git bisect run ./repro.sh`.
- **Many commits between good and bad**: bisect is log₂(n) — even 10,000 commits is ~14 steps. Don't be intimidated.
- **Merge commits**: pass `--first-parent` if you want to bisect only on the mainline.

## Pitfalls

- Bisect lands on a commit that doesn't compile. Mark `git bisect skip` and continue.
- The repro script flaps. Stabilize the script before bisecting.
