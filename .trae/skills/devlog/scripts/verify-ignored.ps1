# verify-ignored.ps1 — assert that local-only files are still ignored by git,
# not tracked in the index, and have never appeared in any commit.
#
# Usage: .\verify-ignored.ps1 [file ...]
#        (defaults to: DEVLOG.md LESSON.md)
# Exit:  0 on success, 1 if any check fails for any file.
#
# Three checks per file (all must pass):
#   1. git check-ignore -v          -> exit 0
#   2. git ls-files --error-unmatch -> exit non-zero
#   3. git log --all --oneline      -> empty

$ErrorActionPreference = 'Continue'

$Files = if ($args.Count -gt 0) { @($args) } else { @('DEVLOG.md', 'LESSON.md') }
$ExitCode = 0

foreach ($f in $Files) {
  # 1. must be ignored
  $ignoreOut = git check-ignore -v -- $f 2>&1
  if ($LASTEXITCODE -eq 0) {
    Write-Host "OK:   $f is ignored  ($ignoreOut)"
  } else {
    Write-Host "FAIL: $f is NOT ignored (git check-ignore returned non-zero)"
    $ExitCode = 1
  }

  # 2. must not be tracked
  $null = git ls-files --error-unmatch -- $f 2>&1
  if ($LASTEXITCODE -ne 0) {
    Write-Host "OK:   $f is not tracked"
  } else {
    Write-Host "FAIL: $f IS tracked in the index (git ls-files matched)"
    $ExitCode = 1
  }

  # 3. must not appear in any commit
  $logOut = (git log --all --oneline -- $f 2>&1) -join "`n"
  if ([string]::IsNullOrWhiteSpace($logOut)) {
    Write-Host "OK:   $f never committed"
  } else {
    Write-Host "FAIL: $f appears in commit history"
    Write-Host "        $logOut"
    $ExitCode = 1
  }
}

if ($ExitCode -eq 0) {
  Write-Host '--- all local-only invariants hold ---'
} else {
  Write-Host '--- one or more invariants BROKEN ---'
}
exit $ExitCode
