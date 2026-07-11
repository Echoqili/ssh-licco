# Design: Hard-Block Dangerous Commands

## Context

`ssh_mcp/security.py::CommandValidator.validate_command` currently runs in two distinct modes:

1. **RELAXED** — checks command against `RELAXED_BLOCKED_PATTERNS` (a small blacklist of catastrophic patterns), then short-circuits past the whitelist and dangerous-character checks.
2. **STRICT / BALANCED** — checks command against a whitelist (`BASE_ALLOWED_COMMANDS` ∪ `EXTENDED_COMMANDS` ∪ user extras), then against dangerous-character regex, then `DANGEROUS_KEYWORDS`.

Risk assessment (`assess_risk_level`) and the multi-layer confirmation gate (`check_multi_layer_confirmation`) are decoupled from `validate_command`. The gate produces warnings and requires `confirm_dangerous=true` plus `confirmation_layer >= required`, but a caller can set both parameters in a single call to bypass every layer. The `approval_id` flow is dead code (the corresponding tools are not registered in `ssh_mcp/server.py::list_tools`).

The result: there is no single chokepoint that *guarantees* a `rm -rf` against an absolute path (or any of a small list of obviously destructive patterns) is rejected before it is sent to the remote shell.

The `execute.py::handle_execute` handler currently calls `check_multi_layer_confirmation` first, then `validate_command`. The order matters: the new hard block must run **before** both, so a hard-blocked command never reaches the warning text or the audit log of "executed after confirmation".

## Goals / Non-Goals

**Goals:**

- Add a single chokepoint in `CommandValidator` that rejects the catastrophic-pattern set regardless of `SSH_SECURITY_LEVEL`, `confirm_dangerous`, or `confirmation_layer`.
- Keep the existing soft signals (risk level, multi-layer confirmation, `RELAXED_BLOCKED_PATTERNS`) intact for backward compatibility and observability, so log dashboards continue to see warnings even when a command passes the soft gate.
- Emit a `WARNING` log line when a hard-block is triggered, with the matched pattern and command.
- Surface a clear, non-overrideable error message to the MCP caller explaining why the command cannot run.

**Non-Goals:**

- Path-prefix allowlists (e.g. "allow `rm -rf` only under `/home/...`") — separate change, requires per-host config.
- Re-introducing the `approval_id` workflow — out of scope; the user explicitly removed it.
- Changing the soft `RELAXED_BLOCKED_PATTERNS` semantics (kept as-is for the relaxed-mode short-circuit).
- Reworking the `RELAXED` short-circuit — keep it, but its hit set is a subset of the new hard block.

## Decisions

### 1. Add `HARD_BLOCKED_PATTERNS` as a class constant, compiled once in `_compile_patterns`

A new class-level constant `HARD_BLOCKED_PATTERNS` is introduced in `CommandValidator`, populated with the catastrophic-operation regex set:

- `rm -rf /`, `rm -rf /*`, `rm -rf /path`, `rm -rf /path/*` (any absolute-path recursive delete, plus the original four `RELAXED_BLOCKED_PATTERNS` lines)
- `mkfs.<fstype>` (any filesystem format)
- `dd if=/dev/(zero|random|urandom) of=/dev/(sd|nvme)` (raw-disk overwrite)
- `:(){:|:&};:` (bash fork-bomb, any whitespace variation)
- `chmod -R (777|000) /` (recursive root perm change)
- `> /dev/(sd|nvme)` and `>> /dev/(sd|nvme)` (raw redirect to disk)

The list is compiled in the existing `_compile_patterns` hook (or a sibling `_compile_hard_block_patterns` to keep concerns separate) and stored as `self._hard_block_regex: list[re.Pattern]`.

**Why not a new class?** A new validator class would force the executor to instantiate both; reusing `CommandValidator` keeps the change localized to one method.

**Why regex, not a string match?** Most existing dangerous patterns are already regex; mixing strategies in the same gate is harder to reason about.

### 2. Hard-block check runs first, unconditionally, in `validate_command`

The new check is the **first** statement after the empty-command guard in `validate_command`. It runs in every security level, including RELAXED, and ignores `confirm_dangerous`. If any pattern matches, raise `SecurityError` with a fixed message that does not mention any override path.

**Why before the RELAXED short-circuit?** The RELAXED branch currently returns early after the relaxed-blocked check, skipping the whitelist. The hard block must run first so RELAXED users do not get a different error path than STRICT/BALANCED users for the same catastrophic command.

**Why raise, not return False?** Matches the existing `SecurityError`-based contract used by all other rejections in this file.

### 3. Multi-layer confirmation is kept but demoted to soft advisory

`check_multi_layer_confirmation` is unchanged. The handler `handle_execute` still calls it first (so soft warnings reach the caller), but the hard block runs *inside* `validate_command`, which the handler calls *after* the soft check. This means a soft warning can be returned to the caller for a `rm -rf /home/user/dir` (HIGH risk, no hard block), but a `rm -rf /etc` (CRITICAL + hard block) is rejected with a hard-block error before any warning text is generated.

Net effect on the four `rm -rf` cases the user asked about:

| Command | Old behavior | New behavior |
|---|---|---|
| `rm file.txt` | SAFE, executes | SAFE, executes |
| `rm -r dir/` | HIGH, soft gate, `confirm_dangerous=true` + `confirmation_layer=2` → executes | HIGH, soft gate still bypassable; **no hard block** |
| `rm -rf relative/dir` | HIGH, same as above | HIGH, same as above; **no hard block** |
| `rm -rf /abs/path` | HIGH in BALANCED, blocked in RELAXED, bypassable in BALANCED with `confirm_dangerous` | **Hard-blocked in all modes, no override** |
| `rm -rf /` | CRITICAL, blocked in RELAXED, bypassable in BALANCED | **Hard-blocked in all modes, no override** |

This is the smallest change that fixes the inconsistency.

### 4. Logging on hard-block

The hard-block branch logs a single `logger.warning` line (using the existing module-level `logger` if present, else `print` to stderr — match the surrounding style in `validate_command`) with the pattern name and the command. The error returned to MCP does **not** echo the regex for security (avoid leaking the blacklist shape), but the log line is fine for SOC consumption.

**Why log, not raise-and-forget?** Hard-block hits are the security-relevant signal we most want in audit. Without a log line, an attacker probing the system gets no record on the server side.

### 5. Tests live in `tests/test_security.py` (new file if absent)

Three new test groups:

- `test_hard_block_rejects_absolute_path_rm_rf` — parametrized over `["rm -rf /", "rm -rf /*", "rm -rf /etc", "rm -rf /var/lib/pg/*"]`, all security levels, with and without `confirm_dangerous`.
- `test_hard_block_rejects_disk_destructive` — `mkfs.ext4 /dev/sda`, `dd if=/dev/zero of=/dev/nvme0n1`, `chmod -R 777 /`.
- `test_soft_risk_still_bypassed_with_confirm` — `rm -rf relative/dir` continues to work with `confirm_dangerous=true, confirmation_layer=2` in BALANCED (regression guard).

## Risks / Trade-offs

- **[Risk] Legitimate bulk-cleanup workflows are now impossible via MCP.** Mitigation: documented in the proposal; operators must use direct SSH login, or use `mv <path> /tmp/.trash_<ts>/` via MCP. A future `path_allowlist` change can restore this safely.
- **[Risk] A bug in the regex set could over-match.** Mitigation: the test suite covers both rejection and non-rejection paths; the patterns are reviewed against the existing `RELAXED_BLOCKED_PATTERNS` (which has been in production) plus a small extension.
- **[Risk] The error message does not tell the user how to actually do the cleanup.** Intentional — leaking the bypass path (or implying one exists) weakens the security stance. The error instead points to the operator documentation.
- **[Trade-off] Soft gate (multi-layer confirmation) is preserved even though it is currently weak.** Kept for now because (a) removing it is a separate concern, (b) it provides observability, (c) some deployments may wire it up to a real `approval_id`-style flow in the future.

## Migration Plan

1. Land the change on a feature branch.
2. Run the test suite locally and in CI.
3. Bump version per project convention (the change affects `ssh_mcp/security.py`, a public module — minor bump).
4. Roll out to staging first; check audit logs for any hard-block hits that indicate existing callers are now broken.
5. If no unexpected hits after 24h, promote to production.
6. Rollback: revert the commit. The hard block is additive; a revert restores the prior behavior exactly.

## Open Questions

- None blocking. If the user later wants a per-host path allowlist, that is a follow-up change (`add-path-allowlist`).
