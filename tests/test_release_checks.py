"""Release preconditions and recovery must fail closed."""

import importlib.util
from pathlib import Path
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "release_checks.py"
spec = importlib.util.spec_from_file_location("release_checks", SCRIPT)
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


@pytest.mark.parametrize("tag", ["master", "v2.8.1", "v2.8.0;echo x", "v2.8.0\n", ""])
def test_invalid_or_mismatched_tag_is_rejected(tag):
    with pytest.raises(ValueError):
        release.validate_tag(tag, "2.8.0")


def test_exact_tag_is_accepted():
    assert release.validate_tag("v2.8.0", "2.8.0") == "2.8.0"


def test_pypi_404_is_the_only_missing_version_response():
    with patch.object(release, "urlopen", side_effect=HTTPError("url", 404, "missing", {}, None)):
        assert release.fetch_pypi("2.8.0") is None


@pytest.mark.parametrize(
    "error",
    [
        HTTPError("url", 403, "denied", {}, None),
        HTTPError("url", 503, "outage", {}, None),
        URLError("offline"),
    ],
)
def test_pypi_errors_do_not_authorize_upload(error):
    with patch.object(release, "urlopen", side_effect=error), patch.object(release.time, "sleep"):
        with pytest.raises(RuntimeError):
            release.fetch_pypi("2.8.0")


def test_malformed_pypi_success_is_rejected():
    response = MagicMock()
    response.__enter__.return_value.read.return_value = b'{"unexpected": true}'
    with patch.object(release, "urlopen", return_value=response):
        with pytest.raises(ValueError):
            release.fetch_pypi("2.8.0")


@pytest.mark.parametrize("present_count", [0, 1, 2])
def test_only_missing_distributions_are_staged(tmp_path, present_count):
    dist = tmp_path / "dist"
    dist.mkdir()
    names = ["ssh_licco-2.8.0-py3-none-any.whl", "ssh_licco-2.8.0.tar.gz"]
    for name in names:
        (dist / name).write_bytes(b"test artifact")
    payload = {"urls": [{"filename": name} for name in names[:present_count]]}
    stage = tmp_path / "upload"
    with patch.object(release, "fetch_pypi", return_value=payload):
        count = release.stage_missing(dist, stage, "2.8.0")
    assert count == 2 - present_count
    assert sorted(p.name for p in stage.iterdir()) == sorted(names[present_count:])


def test_build_must_include_both_distribution_types(tmp_path):
    (tmp_path / "ssh_licco-2.8.0-py3-none-any.whl").write_bytes(b"test")
    with pytest.raises(ValueError):
        release.distributions(tmp_path, "2.8.0")


def test_verify_public_rejects_partial_release(tmp_path):
    for name in ["ssh_licco-2.8.0-py3-none-any.whl", "ssh_licco-2.8.0.tar.gz"]:
        (tmp_path / name).write_bytes(b"test")
    with (
        patch.object(release, "fetch_pypi", return_value={"urls": []}),
        patch.object(release.time, "sleep"),
    ):
        with pytest.raises(RuntimeError):
            release.verify_public(tmp_path, "2.8.0", attempts=2)


def test_documentation_sync_cannot_hide_failing_tests():
    from scripts import sync_docs

    run = MagicMock(returncode=1, stdout="10 passed, 1 failed", stderr="")
    with patch.object(sync_docs.subprocess, "run", return_value=run):
        with pytest.raises(RuntimeError):
            sync_docs.get_test_summary()


@pytest.mark.parametrize("tampered", [False, True])
def test_public_source_comparison_is_portable_and_detects_changes(tmp_path, tampered):
    source = tmp_path / "source"
    installed = tmp_path / "site-packages" / "ssh_mcp"
    (source / "ssh_mcp").mkdir(parents=True)
    installed.mkdir(parents=True)
    (source / "ssh_mcp" / "__init__.py").write_bytes(b"value = 1\r\n")
    (installed / "__init__.py").write_bytes(b"value = 2\n" if tampered else b"value = 1\n")
    spec = MagicMock(origin=str(installed / "__init__.py"))
    with (
        patch.object(release.importlib.metadata, "version", return_value="2.8.0"),
        patch.object(release.importlib.util, "find_spec", return_value=spec),
    ):
        if tampered:
            with pytest.raises(ValueError, match="differs"):
                release.verify_installed(source, "2.8.0")
        else:
            release.verify_installed(source, "2.8.0")
