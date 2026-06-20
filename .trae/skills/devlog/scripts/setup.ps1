# setup.ps1 — one-shot initialization for the devlog skill in the current project.
# Creates DEVLOG.md and LESSON.md (if missing), registers them in
# .git/info/exclude (idempotent), and verifies the ignore is working.
#
# Usage:  .\setup.ps1
#         (run from the project root; safe to re-run)

$ErrorActionPreference = 'Stop'

# ---------- guards ----------
if (-not (Test-Path .git)) {
  Write-Error "not a git repository (.git/ not found). Run from a project root."
}

New-Item -ItemType Directory -Force -Path .git/info | Out-Null
if (-not (Test-Path .git/info/exclude)) {
  New-Item -ItemType File -Path .git/info/exclude | Out-Null
}

# ---------- helpers ----------
function Add-ToExclude {
  param([string]$Pattern)
  $excludeFile = '.git/info/exclude'
  $existing = Get-Content $excludeFile -ErrorAction SilentlyContinue
  if (-not ($existing -contains $Pattern)) {
    Add-Content $excludeFile "`n# Local-only devlog (see .trae/skills/devlog/SKILL.md)"
    Add-Content $excludeFile $Pattern
  }
}

$devlogTemplate = @'
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
'@

$lessonTemplate = @'
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
'@

# ---------- main ----------
if (-not (Test-Path DEVLOG.md)) {
  Set-Content -Path DEVLOG.md -Value $devlogTemplate -Encoding UTF8
  Write-Host "created: DEVLOG.md"
}
Add-ToExclude 'DEVLOG.md'

if (-not (Test-Path LESSON.md)) {
  Set-Content -Path LESSON.md -Value $lessonTemplate -Encoding UTF8
  Write-Host "created: LESSON.md"
}
Add-ToExclude 'LESSON.md'

Write-Host '--- verification ---'
git check-ignore -v DEVLOG.md LESSON.md

Write-Host '--- done ---'
Write-Host 'DEVLOG.md and LESSON.md are now local-only.'
Write-Host 'Both files live in this project but will never be pushed to remote.'
