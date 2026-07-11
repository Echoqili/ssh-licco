# Hard-Block Dangerous Commands

## Why

The current command validation pipeline has a structural weakness: a small set of catastrophic operations (e.g. `rm -rf /`, `mkfs.*`, `dd if=/dev/... of=/dev/...`, `chmod -R 777 /`) can still reach the remote shell under certain paths. The existing mitigations are either a soft blacklist (only enforced in RELAXED mode, only matches absolute paths), a non-functional "multi-layer confirmation" that can be bypassed in a single call by setting `confirm_dangerous=true` and `confirmation_layer=N` together, or a removed `approval_id` mechanism whose tools are no longer registered with the MCP server. As a result, there is **no real hard gate** stopping a high-risk `rm -rf` from executing today. We need a single, mode-independent, non-bypassable hard block for a small list of obviously destructive patterns.

## What Changes

- Introduce a new `HARD_BLOCKED_PATTERNS` list in `ssh_mcp/security.py` containing the catastrophic-operation patterns (root-deletion, absolute-path recursive deletion, disk-formatting, raw-disk `dd`, fork-bomb, root-permission `chmod`, etc.).
- Refactor `CommandValidator.validate_command` so the hard-block check runs **before** any whitelist, relaxed-blacklist, dangerous-character, or `confirm_dangerous` logic, and **cannot be bypassed** by `confirm_dangerous`, `confirmation_layer`, `SSH_SECURITY_LEVEL`, or any other env var.
- Keep the existing `RELAXED_BLOCKED_PATTERNS` for backward compatibility but make it a strict subset of `HARD_BLOCKED_PATTERNS` (or merge them — the net effect must be: those patterns are blocked in all modes).
- Update `DANGEROUS_COMMAND_PATTERNS` so risk assessment is still useful for logging/audit (HIGH/CRITICAL label remains for observability) but is no longer used as a gating condition for the hard-block list.
- Update the error message returned for hard-blocked commands to clearly state that the command is rejected unconditionally and cannot be overridden by any parameter.

**BREAKING**: Any caller previously relying on `confirm_dangerous=true` to execute `rm -rf /path` (or similar) will now receive a hard-block error. This is an intentional security tightening. The recommended replacement is `mv` to a trash directory, or a per-host path allowlist (out of scope for this change).

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- **`ssh-security`**: Add a new requirement `Hard Block on Catastrophic Commands` that is independent of `SSH_SECURITY_LEVEL`, `confirm_dangerous`, and `confirmation_layer`. The existing `Command Validation` requirement's "Dangerous command blocked" scenario is extended to cover the new patterns.

## Impact

- **Code**: `ssh_mcp/security.py` (new constant, refactored `validate_command`), `ssh_mcp/handlers/execute.py` (error message handling — minimal), `openspec/specs/ssh-security/spec.md` (delta).
- **API**: No new MCP tools. The `ssh_execute` tool's `confirm_dangerous` parameter keeps its current shape; only its semantics change (it still bypasses the soft multi-layer confirmation, but never the hard block).
- **Backward compatibility**: A user who today runs `rm -rf /home/user/junk` via `confirm_dangerous=true` will be blocked after this change. Mitigation: replace with `mv /home/user/junk /tmp/.trash_<ts>/` or similar.
- **Tests**: Add unit tests in `tests/` (or extend existing) covering: (a) hard-blocked pattern is rejected with `confirm_dangerous=true`, (b) hard-blocked pattern is rejected in all three security levels, (c) safe `rm file.txt` and `rmdir` continue to work.
- **Audit logging**: When a command is hard-blocked, emit a WARNING log line containing the matched pattern and risk level, so SOC dashboards can detect misuse attempts.

## Security Impact

This change **raises the security floor** by closing the previously exploitable path where a `rm -rf` could reach the remote shell. The change is intentionally irreversible-by-config so that a misconfigured `SSH_SECURITY_LEVEL=relaxed` or a forgotten `confirm_dangerous=true` cannot re-introduce the risk. The trade-off is loss of convenience: legitimate but heavy cleanup operations (e.g. wiping a known staging directory) can no longer be done in a single MCP call. Operators must perform those operations out-of-band (direct SSH login, or a future `path_allowlist` feature). No new attack surface is introduced.
