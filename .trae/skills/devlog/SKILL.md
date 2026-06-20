---
name: "devlog"
description: "Use when the user wants to record a code change, plan, decision, bug fix, or library gotcha in a project. Maintains a per-project DEVLOG.md (chronological, append-only) and a LESSON.md (indexed knowledge base of problem → root cause → solution). Triggers on phrases like 'log this', '记一下', '记到 DEVLOG', '记到 LESSON', '做个总结', 'save a lesson', 'remember this gotcha', or after completing a coding task, making an architectural decision, or fixing a non-trivial bug. Both files stay local-only via .git/info/exclude. Do NOT use for short-lived TODOs (use the issue tracker) or for public notes (use a wiki)."
license: MIT
compatibility: "Requires git. No external dependencies. POSIX shell (bash/zsh) or PowerShell 5+ for the setup scripts."
metadata:
  version: "1.1.0"
  author: "Trae IDE devlog skill"
---

# DEVLOG Skill

Maintain **two** local-only project files that work together:

| File | Role | Style |
|---|---|---|
| `DEVLOG.md` | Chronological log of what was done, planned, and learned | Append-only, dated entries |
| `LESSON.md` | Aggregated knowledge base of problems → root causes → solutions | Indexed, category-organized, reusable |

Rule of thumb: **DEVLOG.md records the journey; LESSON.md records the wisdom.**

Both files are **local-only** — they must never reach the remote repository, and
the ignore rules for them must not be committed either. This is achieved with
`.git/info/exclude` (a per-repo, never-tracked file), **not** `.gitignore`.

## When to Use

Invoke this skill when any of the following happen:

- Starting a new coding task in a project
- Completing a coding task or a significant sub-step
- Making an architectural or design decision
- Fixing a non-trivial bug
- Discovering a library / framework gotcha
- User says things like "log this", "记一下", "记到 DEVLOG", "记到 LESSON",
  "做个总结", "加到 LESSON", "save a lesson", "remember this gotcha"

## When NOT to Use

- **Short-lived TODOs** — use the project issue tracker or a local TODO file.
- **Public-facing documentation** — use the project wiki or a shared doc.
- **Free-form chat summaries** — use conversation search, not a log file.
- **Secrets, credentials, or PII** — never store in either file, even though
  they are local.
- **One-line trivial commits** — skip; only log meaningful changes.

## First-Run Setup

On first invocation in a project (or if either file is missing):

1. Run the platform-appropriate setup script — it creates both files from
   templates and registers them in `.git/info/exclude`:

   ```bash
   # POSIX (bash, zsh, Git Bash, WSL)
   ./.trae/skills/devlog/scripts/setup.sh
   ```
   ```powershell
   # Windows PowerShell 5+
   ./.trae/skills/devlog/scripts/setup.ps1
   ```

   The script is **idempotent** — safe to re-run.

2. Verify with: `git check-ignore -v -- DEVLOG.md LESSON.md`
   - Expected: both lines reference `.git/info/exclude`.

3. Tell the user both files are intentionally local-only.

If the files already exist, just read them for context and append. Never
recreate. For background on the ignore choice, see
[references/git-exclude-explained.md](references/git-exclude-explained.md).

---

# DEVLOG.md

Append-only chronological log.

## Entry Format

```markdown
## [YYYY-MM-DD] Brief title

**What:** One sentence describing what was done.
**Why:** The trigger, problem, or motivation.
**How:** Key implementation details (non-obvious only).
**Learned:** Gotchas, patterns, follow-ups, or open questions.
```

Conventions:

- Date in user's local timezone, ISO `YYYY-MM-DD`.
- Title: short noun phrase, no period.
- Bullets are fine inside any field.
- Never edit or delete old entries — only append.
- When a fix surfaces reusable knowledge, add a pointer:
  `**Lesson:** see LESSON.md → <Category> → <slug>`

## Workflow

### On task start

1. Read `DEVLOG.md` (if present) for context and the `## Planned` section.
2. If a `## Planned` item matches the current task, note it in the upcoming entry.

### On task completion / decision

1. Read the current `DEVLOG.md`.
2. Append a new `## [YYYY-MM-DD]` block under the existing content.
3. If a planned item is now done, move it from `## Planned` into a dated entry
   with a `[Done]` prefix in the title (do not delete the original line — strike
   it through or annotate it).
4. Add follow-up items to `## Planned` if any.
5. **Promote** to `LESSON.md` if the learning is reusable (see below).

### Hygiene

- If the file grows past ~300 entries, split by year (`DEVLOG-2026.md`) and keep
  `DEVLOG.md` as an index.
- Never include secrets — treat it as plain text even though it's local.

---

# LESSON.md

Aggregated, searchable knowledge base of problems and their solutions. Where
`DEVLOG.md` is a stream, `LESSON.md` is an index — each lesson is a stable
entry that can be referenced, linked, and re-applied.

## When to Promote DEVLOG → LESSON

Promote a `DEVLOG.md` entry into `LESSON.md` when **any** of these is true:

- The same root cause could appear again in this project (or in similar ones).
- The fix took more than ~15 minutes of investigation.
- A library / framework behaved counter to docs or intuition.
- The user asked "why did we do it this way?" — i.e. the rationale is valuable
  out of context.

If the issue was trivial or one-off, keep it only in `DEVLOG.md`.

## Entry Format

Group by **category** (one `##` heading per category). Slugs are stable IDs you
can link to.

```markdown
## <Category, e.g. "Library / React">

### <YYYY-MM-DD> short-slug

- **Problem:** One-sentence description of the symptom.
- **Root cause:** Why it happened.
- **Solution:** The fix (commands, code, config).
- **How to avoid:** Checklist, lint rule, or convention to prevent recurrence.
- **Related:**
  - `DEVLOG.md` → `## [YYYY-MM-DD] <title>`
  - upstream issue / docs link
```

For the canonical category list and naming rules, see
[references/categories.md](references/categories.md).

Conventions:

- `Problem` is the user-visible symptom. `Root cause` is the underlying reason.
  Keep them separate — symptoms recur even when causes change.
- Slug = lowercase-kebab, ≤ 5 words, action-oriented
  (e.g. `push-fails-on-spaces-in-path`).
- Newest lesson at the **top** of its category, so the freshest knowledge is
  most visible.

## Workflow

### When a non-trivial bug is fixed

1. Open `LESSON.md` and pick (or create) the right category.
2. Add a new entry at the top of that category with the template above.
3. Cross-link from the matching `DEVLOG.md` entry
   (`**Lesson:** see LESSON.md → <Category> → <slug>`).
4. If this exact lesson already exists, **append** a new dated occurrence under
   it instead of creating a duplicate — frequency matters.

### When starting a task

1. Read the relevant categories in `LESSON.md` before designing the approach.
2. If the user says "have we seen this before?" — search the file first.

### Hygiene

- Never delete a lesson. If advice is wrong or outdated, strike it through and
  add a "Superseded by" note.
- Keep entries terse — one screen each, ideally.
- After ~50 lessons, add a top-of-file **Index** table grouped by category.

---

## Examples

The following worked examples show what a good log entry looks like for common
trigger scenarios. Match the **shape** (fields, terseness, cross-links) — the
exact wording can vary.

### Example 1: logging a feature

User: "Add a `/health` endpoint that returns 200 if the DB is reachable."

Append to `DEVLOG.md`:

```markdown
## [2026-06-19] Add /health endpoint with DB ping

**What:** Added GET /health that returns 200 with `{db: "ok"}` if the
PostgreSQL connection works, 503 otherwise.
**Why:** k8s liveness/readiness probes were killing the pod on transient
DB hiccups — they need a real signal, not just "process is up".
**How:** Used `pg.Pool.query('SELECT 1')` with a 1s timeout. Catches the
error and returns 503. No body on failure to keep probes cheap.
**Learned:** A common gotcha is to return 200 unconditionally after a
catch — that hides the very problem probes exist to detect.
```

### Example 2: logging a bug fix + promoting to LESSON

User: "Why did `git push` fail with 'Authentication failed' even though my
token is in the credential helper?"

Append to `DEVLOG.md`:

```markdown
## [2026-06-19] Fix GitHub push auth failure on Windows

**What:** Got `fatal: Authentication failed for https://github.com/...`
on every push despite `gh auth login` succeeding.
**Why:** `gh auth` writes the token to the GitHub CLI credential helper,
but `git push` was reading the system Git credential helper (no token
there). They don't share storage.
**How:** Configured the system helper to delegate to the GitHub CLI
helper: `git config --global credential.helper '!gh auth git-credential'`.
**Lesson:** see LESSON.md → Git → gh-auth-vs-git-credential-mismatch
**Learned:** `gh auth` ≠ git auth. Tools that wrap git often have their
own credential store.
```

Then add to `LESSON.md` (top of the `## Git` section):

```markdown
## Git

### 2026-06-19 gh-auth-vs-git-credential-mismatch

- **Problem:** `git push` fails with auth error after `gh auth login`
  succeeded on the same machine.
- **Root cause:** `gh auth` stores its token in its own credential
  helper. Plain `git` uses whatever is configured in
  `credential.helper` (often the system store or `manager-core` on
  Windows). They don't share.
- **Solution:** Delegate the git credential helper to gh:
  `git config --global credential.helper '!gh auth git-credential'`
- **How to avoid:** When you authenticate with `gh`, also re-run the
  delegate command. Document this in the team onboarding README.
- **Related:**
  - DEVLOG.md → ## [2026-06-19] Fix GitHub push auth failure on Windows
  - https://cli.github.com/manual/gh_auth
```

### Example 3: logging a tricky library gotcha

User: "Python's `dict | dict` merge sometimes loses keys, why?"

Append to `DEVLOG.md`:

```markdown
## [2026-06-19] Python `|` dict merge: dict-of-dict gotcha

**What:** `a = {"x": {"a": 1}}; b = {"x": {"b": 2}}; merged = a | b`
gives `{"x": {"b": 2}}` — `a.x.a` is gone.
**Why:** PEP 584 `dict.__or__` replaces the *value* of each key, it does
not recurse. So nested dicts at the same key overwrite, not merge.
**How:** Use `{**a["x"], **b["x"]} | {"x": ...}` for the inner layer,
or `deepmerge` / `pydantic` for arbitrary depth.
**Lesson:** see LESSON.md → Language / Python → dict-or-merge-no-recurse
**Learned:** `|` looks like `dict.update` but is shallow; matches
`{**a, **b}` semantics, not `ChainMap`.
```

Then add to `LESSON.md` (top of `## Language / Python`):

```markdown
## Language / Python

### 2026-06-19 dict-or-merge-no-recurse

- **Problem:** `a | b` for nested dicts silently drops keys.
- **Root cause:** `dict.__or__` is shallow — replaces values, doesn't
  recurse into dicts.
- **Solution:** Use `{**a["k"], **b["k"]} | ...` per layer, or a deep
  merge library (`deepmerge`, `pydantic`).
- **How to avoid:** In code review, flag any `|` on values that might
  be dicts. Add a linter rule if your team uses dicts as config.
- **Related:**
  - DEVLOG.md → ## [2026-06-19] Python `|` dict merge: dict-of-dict gotcha
  - https://peps.python.org/pep-0584/
```

### Categories at a glance

Quick reference for picking a `## <Category>` heading in `LESSON.md`. The full
table with naming rules is in [references/categories.md](references/categories.md).
Inline version is for quick decision-making at the moment of writing a new
lesson; load the reference when you need naming details.

| Category | Use for |
|---|---|
| `Git` | Branching, history, ignore rules, hooks, submodules |
| `Build` | Bundlers, compilers, packaging |
| `CI` | GitHub Actions, GitLab CI, test runners in CI |
| `Language / <name>` | Per-language quirks (`Language / Python`, `Language / TypeScript`, ...) |
| `Library / <name>` | Specific third-party libraries (`Library / React`, `Library / FastAPI`, ...) |
| `OS / Windows` | PowerShell, paths, line endings |
| `OS / macOS` | Gatekeeper, codesign, BSD vs GNU tools |
| `OS / Linux` | Distros, package managers, systemd |
| `IDE / Trae` | Trae IDE, MCP servers, custom skills |
| `Networking` | DNS, HTTP, proxies, CORS, certificates |
| `Performance` | Profiling, optimization, memory, latency |
| `Security` | Auth, secrets, vulnerabilities, secure defaults |
| `Testing` | Test frameworks, mocks, fixtures, coverage |
| `Debugging` | `strace`, `pdb`, profilers, observability tools |

Trigger logic for choosing one:

1. If the lesson is a **library / framework gotcha** → `Library / <name>` or
   `Language / <name>`.
2. If it's about the **OS shell or filesystem** → `OS / <platform>`.
3. If it's about the **build / CI / test pipeline** → `Build` / `CI` / `Testing`.
4. If it's about **this development environment** (Trae, IDEs, MCP) →
   `IDE / Trae`.
5. Otherwise → `Git` / `Networking` / `Performance` / `Security` /
   `Debugging` — pick the closest.

Rule: prefer the closest existing category. Add a new one only after ~3
lessons accumulate that don't fit anywhere (see
[references/categories.md](references/categories.md) for the policy).

---

## Anti-Patterns

- Do **not** add `DEVLOG.md` or `LESSON.md` to `.gitignore` — that pushes the
  ignore rule to the remote, which the user explicitly does not want. Use
  `.git/info/exclude`. *Consequence:* teammates would inherit a rule that only
  protects *your* local notes.
- Do **not** commit either file "just this once" — once tracked, ignore rules
  no longer hide them. Recover with `git rm --cached <file>` and warn the user.
- Do **not** rewrite or delete past `DEVLOG.md` entries — they form the audit
  trail that `LESSON.md` is distilled from.
- Do **not** store secrets, tokens, or credentials in either file.
- Do **not** duplicate information — pick one: chronological (`DEVLOG.md`) or
  indexed (`LESSON.md`), and cross-link.
- Do **not** use this skill for public docs, short-lived TODOs, or chat
  summaries — see **When NOT to Use**.

## File Layout

```
.trae/skills/devlog/
├── SKILL.md                          # this file
├── scripts/
│   ├── setup.sh                      # POSIX one-shot init
│   ├── setup.ps1                     # PowerShell one-shot init
│   ├── verify-ignored.sh             # assert local-only files stay untracked
│   └── verify-ignored.ps1            # PowerShell counterpart
└── references/
    ├── git-exclude-explained.md      # why .git/info/exclude
    └── categories.md                 # canonical LESSON.md categories
```

Generated files in the user's project (created by `scripts/setup.*`):

- `DEVLOG.md` (local-only)
- `LESSON.md` (local-only)

After setup, run `./scripts/verify-ignored.sh` (or `.ps1`) to confirm both
files satisfy the local-only invariant (ignored, untracked, never committed).
Re-run it any time you suspect the invariant has been broken.
