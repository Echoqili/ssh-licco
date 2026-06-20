#!/usr/bin/env bash
# verify-ignored.sh — assert that local-only files are still ignored by git,
# not tracked in the index, and have never appeared in any commit.
#
# Usage: ./verify-ignored.sh [file ...]
#        (defaults to: DEVLOG.md LESSON.md)
# Exit:  0 on success, 1 if any check fails for any file.
#
# Three checks per file (all must pass):
#   1. git check-ignore -v       -> exit 0
#   2. git ls-files --error-unmatch -> exit non-zero
#   3. git log --all --oneline   -> empty

set -euo pipefail

FILES=("$@")
if [ "${#FILES[@]}" -eq 0 ]; then
  FILES=(DEVLOG.md LESSON.md)
fi

exit_code=0

for f in "${FILES[@]}"; do
  # 1. must be ignored
  if ignore_line="$(git check-ignore -v -- "$f" 2>/dev/null)"; then
    echo "OK:   $f is ignored  ($ignore_line)"
  else
    echo "FAIL: $f is NOT ignored (git check-ignore returned non-zero)"
    exit_code=1
  fi

  # 2. must not be tracked
  if git ls-files --error-unmatch -- "$f" >/dev/null 2>&1; then
    echo "FAIL: $f IS tracked in the index (git ls-files matched)"
    exit_code=1
  else
    echo "OK:   $f is not tracked"
  fi

  # 3. must not appear in any commit
  if [ -n "$(git log --all --oneline -- "$f" 2>/dev/null)" ]; then
    echo "FAIL: $f appears in commit history"
    git log --all --oneline -- "$f" | sed 's/^/        /'
    exit_code=1
  else
    echo "OK:   $f never committed"
  fi
done

if [ $exit_code -eq 0 ]; then
  echo "--- all local-only invariants hold ---"
else
  echo "--- one or more invariants BROKEN ---"
fi
exit $exit_code
