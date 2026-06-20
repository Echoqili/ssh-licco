# Why `.git/info/exclude` (not `.gitignore`) for local-only files

This skill intentionally uses `.git/info/exclude` instead of `.gitignore` for
the local-only log files (`DEVLOG.md`, `LESSON.md`). The user requirement:
**ignore the file AND keep the ignore rule itself off the remote.**

## Quick decision tree

```
Need the rule to apply to the whole team / new clones?
├── Yes → .gitignore (tracked, shared)
└── No
    ├── Applies to every repo on this machine?  → core.excludesFile (global)
    └── Only this repo, only this machine?      → .git/info/exclude  ← devlog uses this
```

## The three mechanisms

| Mechanism | Versioned? | Scope | Example use |
|---|---|---|---|
| `.gitignore` | **Yes** (tracked) | Whole repo, all clones | `node_modules/`, `dist/`, `__pycache__/` |
| `.git/info/exclude` | **No** (in `.git/`) | This repo, this machine | Personal notes, scratch files |
| `core.excludesFile` | No | Global, all repos | `.DS_Store`, personal editor cruft |

## How to add a rule to `.git/info/exclude`

PowerShell:

```powershell
Add-Content .git/info/exclude 'DEVLOG.md'
```

POSIX shell:

```bash
printf '%s\n' 'DEVLOG.md' >> .git/info/exclude
```

The path is easy to flip in your head — it is **not** `.git/exclude/info`, it
is `.git/info/exclude`. The file already exists in every Git repo; you should
not need to create it (just `touch` if a paranoid tool removed it).

## How to verify a rule works

```bash
git check-ignore -v -- DEVLOG.md
```

Expected output (rule came from `.git/info/exclude`):

```
.git/info/exclude:9:DEVLOG.md   DEVLOG.md
```

No output = Git did not match any rule. Check the path, the pattern, and the
spelling of `.git/info/exclude`.

## Edge cases

- **Already tracked?** `git ls-files -- DEVLOG.md` will print the path. Ignore
  rules only apply to **untracked** files. Recover with
  `git rm --cached DEVLOG.md` and warn the user, since this affects all
  collaborators who pull.
- **Multi-checkout monorepos?** `.git/info/exclude` is per-checkout, which is
  usually what you want — each developer has their own log.
- **Submodules?** The rule lives in the superproject. Submodules need their
  own `.git/info/exclude` if you want the same effect there.
- **Patterns vs. file paths?** Same glob syntax as `.gitignore`. `**/DEVLOG.md`
  matches at any depth; `DEVLOG.md` matches the project root only.

## This is not secret management

Ignore rules help avoid accidental commits; they do not make a file safe. Even
though `DEVLOG.md` / `LESSON.md` are local, treat them as plain text — never
put credentials, tokens, or PII in them. For shared secrets use `.env` + a
proper secrets manager.
