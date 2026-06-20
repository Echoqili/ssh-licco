# LESSON.md Categories

Canonical category list for `LESSON.md` entries. Use one `## <Category>` heading
per group. Load this file only when you need to pick a category — the SKILL.md
default workflow covers most cases.

## Standard categories

| Category | When to use |
|---|---|
| `Git` | `.gitignore`, branching, hooks, submodules, rebase/merge, history rewriting |
| `Build` | Bundlers, compilers, transpilers, packaging (webpack, vite, esbuild, setuptools) |
| `CI` | GitHub Actions, GitLab CI, Jenkins, test runners in CI |
| `Language / <name>` | Per-language quirks (e.g. `Language / Python`, `Language / TypeScript`) |
| `Library / <name>` | Specific third-party libraries (e.g. `Library / React`, `Library / FastAPI`) |
| `OS / Windows` | Windows-specific behavior (PowerShell, paths, line endings) |
| `OS / macOS` | macOS-specific behavior (Gatekeeper, codesign, BSD vs GNU tools) |
| `OS / Linux` | Linux-specific behavior (distros, package managers, systemd) |
| `IDE / Trae` | Trae IDE behavior, MCP servers, custom skills |
| `Networking` | DNS, HTTP, proxies, CORS, certificates |
| `Performance` | Profiling, optimization, memory leaks, latency |
| `Security` | Auth, secrets, vulnerabilities, secure defaults |
| `Testing` | Test frameworks, mocks, fixtures, coverage |
| `Debugging` | Tools and techniques for finding bugs (strace, pdb, profilers) |

## Naming rules

- **Singular, Title-Case, ASCII only.** `Git`, not `gits` or `GIT`.
- **Sub-namespace with ` / `** when needed: `Language / Python`, not
  `Python language` or `Language-Python`.
- **Avoid ephemeral categories** (project codenames, ticket numbers) — those
  belong in `DEVLOG.md`, not `LESSON.md`.
- **Prefer existing categories** over inventing new ones. If three lessons
  don't fit anywhere, *then* add a new category.

## When to add a new category

Add a new `## <Category>` heading only when **at least 3 lessons** have
accumulated that don't fit any existing category. Otherwise use the closest
match and tag the project / library in the slug or `Related` section.

## When to split or merge categories

- **Split** a category if it grows past ~25 lessons and sub-themes emerge
  (e.g. `Library / React` → `Library / React Hooks`).
- **Merge** if a category has <3 lessons after 6 months — fold it into the
  nearest existing category.
- **Rename** is forbidden once entries exist — slugs and category names are
  stable IDs. If a rename is truly needed, add a `Superseded by:` note at the
  top of the old category and create the new one.
