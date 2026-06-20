#!/usr/bin/env bash
# setup.sh — one-shot initialization for the devlog skill in the current project.
# Creates DEVLOG.md and LESSON.md (if missing), registers them in
# .git/info/exclude (idempotent), and verifies the ignore is working.
#
# Usage:  ./setup.sh
#         (run from the project root; safe to re-run)

set -euo pipefail

# ---------- guards ----------
if [ ! -d .git ]; then
  echo "error: not a git repository (.git/ not found). Run from a project root." >&2
  exit 1
fi

mkdir -p .git/info
touch .git/info/exclude

# ---------- helpers ----------
add_to_exclude() {
  local pattern="$1"
  local exclude_file=".git/info/exclude"
  if ! grep -Fxq "$pattern" "$exclude_file"; then
    printf '\n# Local-only devlog (see .trae/skills/devlog/SKILL.md)\n%s\n' "$pattern" >> "$exclude_file"
  fi
}

write_devlog_template() {
  cat > DEVLOG.md <<'EOF'
# DEVLOG

> Local-only development log. Intentionally **not** tracked by git
> (configured via `.git/info/exclude`, never via `.gitignore`).

Conventions:

- One `## [YYYY-MM-DD] Title` block per logical change.
- Fields: **What**, **Why**, **How**, **Learned**.
- Append-only — never rewrite history.

---

## Planned

- (in-progress or upcoming work goes here)

---
EOF
}

write_lesson_template() {
  cat > LESSON.md <<'EOF'
# LESSON

> Local-only knowledge base. Aggregates problems → root causes → solutions
> from `DEVLOG.md`. Intentionally **not** tracked by git
> (configured via `.git/info/exclude`, never via `.gitignore`).

Conventions:

- Grouped by category (`## <Category>`), newest lesson at the top of each.
- Entry format: **Problem / Root cause / Solution / How to avoid / Related**.
- Slugs are stable IDs — never rename an old slug, only add "Superseded by".

See `.trae/skills/devlog/references/categories.md` for the canonical category list.

---

## Index

(to be generated once the file has more than ~10 lessons)

---
EOF
}

# ---------- main ----------
if [ ! -f DEVLOG.md ]; then
  write_devlog_template
  echo "created: DEVLOG.md"
fi
add_to_exclude "DEVLOG.md"

if [ ! -f LESSON.md ]; then
  write_lesson_template
  echo "created: LESSON.md"
fi
add_to_exclude "LESSON.md"

echo "--- verification ---"
git check-ignore -v DEVLOG.md LESSON.md

echo "--- done ---"
echo "DEVLOG.md and LESSON.md are now local-only."
echo "Both files live in this project but will never be pushed to remote."
