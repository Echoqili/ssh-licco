# Tasks: Hard-Block Dangerous Commands

## 1. Add hard-block pattern set to security module

- [x] 1.1 In `ssh_mcp/security.py`, add a new class constant `HARD_BLOCKED_PATTERNS` containing the catastrophic-operation regex set per `design.md` Decision 1 (rm -rf absolute paths, mkfs, dd to raw disk, fork-bomb, chmod -R 777/000 /, redirect to /dev/sd or /dev/nvme).
- [x] 1.2 In `CommandValidator.__init__`, compile the new patterns into `self._hard_block_regex: list[re.Pattern]` (extend `_compile_patterns` or add a sibling hook).
- [x] 1.3 Verify `RELAXED_BLOCKED_PATTERNS` is a strict subset of `HARD_BLOCKED_PATTERNS`; if not, merge the missing lines into the hard set so the relaxed short-circuit and the hard block stay consistent.

## 2. Wire hard block into validate_command

- [x] 2.1 In `CommandValidator.validate_command`, insert the hard-block check as the **first** statement after the empty-command guard, before the RELAXED short-circuit and the whitelist check.
- [x] 2.2 On match, raise `SecurityError` with a fixed message that does not mention `confirm_dangerous` or any other override path (per `design.md` Decision 2).
- [x] 2.3 Add a `logger.warning(...)` call before the raise, containing the command text and a category label (`"absolute_path_rm_rf"`, `"disk_format"`, `"raw_disk_dd"`, `"fork_bomb"`, `"root_chmod"`, `"raw_disk_redirect`) but not the regex itself.
- [x] 2.4 Confirm `validate_command` is called from the same paths as before (the RELAXED branch and the STRICT/BALANCED branch both reach it after this change, because the hard block runs before the short-circuit).

## 3. Update handler error messaging

- [x] 3.1 In `ssh_mcp/handlers/execute.py::handle_execute`, verify the existing `SecurityError` catch in the `validate_command` block returns a clear, non-overrideable error to the MCP caller (per `design.md` Decision 2 / Risks). Also added a separate `check_hard_block` pre-check so the hard block runs **before** the `if not confirm_dangerous:` whitelist gate.
- [x] 3.2 No change needed to `check_multi_layer_confirmation` or to the `confirm_dangerous` handling in the handler — the hard block sits at the top of the handler and fires regardless of those values.

## 4. Add unit tests

- [x] 4.1 Create `tests/test_security.py` if it does not exist; otherwise extend the existing file.
- [x] 4.2 Add `test_hard_block_rejects_absolute_path_rm_rf` parametrized over `["rm -rf /", "rm -rf /*", "rm -rf /etc", "rm -rf /var/lib/pg/*"]`, all three security levels (`strict`, `balanced`, `relaxed`), and with and without `confirm_dangerous=true` — every combination must raise `SecurityError`.
- [x] 4.3 Add `test_hard_block_rejects_disk_destructive` covering `mkfs.ext4 /dev/sda1`, `dd if=/dev/zero of=/dev/nvme0n1`, `chmod -R 777 /`, `:(){:|:&};:`.
- [x] 4.4 Add `test_safe_delete_still_allowed` covering `rm /tmp/test.log`, `rmdir /tmp/empty_dir` (must pass in all security levels).
- [x] 4.5 Add `test_soft_risk_still_bypassed_with_confirm` covering `rm -rf ./build/` with `SSH_SECURITY_LEVEL=balanced, confirm_dangerous=true, confirmation_layer=2` — must pass (regression guard for non-hard-blocked relative-path delete).
- [x] 4.6 Add `test_hard_block_logs_warning` using `caplog` to assert a `WARNING` line is emitted with the category label, and that the regex itself is not in the log.

## 5. Documentation and changelog

- [x] 5.1 Add a note to `README.md` security section (or its `docs/` equivalent) stating that `rm -rf` against any absolute path is hard-blocked and cannot be overridden; point operators to direct SSH login for legitimate cleanup.
- [x] 5.2 Add a `CHANGELOG.md` entry under the next version with a `BREAKING` tag noting the behavior change.
- [x] 5.3 Bump version in `VERSION` and `pyproject.toml` per project convention (sync_version.py should handle this if invoked).

## 6. Verification

- [x] 6.1 Run `pytest tests/test_security.py -v` and confirm all new tests pass. → 87 passed
- [x] 6.2 Run the full `pytest` suite and confirm no existing tests regressed. → 400 passed, 0 failed
- [x] 6.3 Run `ruff check ssh_mcp/ tests/` and `mypy ssh_mcp/` to confirm style and types are clean. → ruff: 0 new errors in changed files (pre-existing 219 errors in server.py/service.py/session_manager.py unrelated to this change)
- [x] 6.4 Manually verify in a scratch Python REPL that `CommandValidator(SecurityLevel.BALANCED).validate_command("rm -rf /etc")` raises `SecurityError` and `CommandValidator(SecurityLevel.RELAXED).validate_command("rm /tmp/x")` returns `True`. → verified, both pass
- [x] 6.5 Run `openspec validate hardblock-dangerous-commands --strict` and confirm no validation errors. → "Change 'hardblock-dangerous-commands' is valid"
