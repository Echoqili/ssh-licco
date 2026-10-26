"""Registry authentication responses must never expose credentials in CI logs."""

from unittest.mock import MagicMock, patch

import pytest

from scripts import publish_mcp_registry as registry


@pytest.mark.parametrize("status", [200, 403])
def test_authentication_response_is_not_logged(status, capsys):
    response = MagicMock(status_code=status)
    response.text = '{"registry_token": "sensitive-registry-token"}'
    response.json.return_value = {"registry_token": "sensitive-registry-token"}
    with (
        patch.object(registry, "GITHUB_TOKEN", "sensitive-github-token"),
        patch.object(registry.requests, "post", return_value=response),
    ):
        registry.login_registry()
    output = capsys.readouterr().out
    assert "sensitive-registry-token" not in output
    assert "sensitive-github-token" not in output


def test_registry_publish_error_body_is_not_logged(capsys):
    response = MagicMock(status_code=403, text="sensitive-registry-token")
    response.json.return_value = {"error": "sensitive-registry-token"}
    with (
        patch.object(registry, "get_version", return_value="2.8.0"),
        patch.object(registry.requests, "post", return_value=response),
    ):
        assert registry.publish_to_registry("sensitive-registry-token") is False
    assert "sensitive-registry-token" not in capsys.readouterr().out


def test_missing_version_never_publishes_a_fallback():
    with (
        patch.object(registry, "get_version", return_value=None),
        patch.object(registry.requests, "post") as post,
    ):
        assert registry.publish_to_registry("unused") is False
    post.assert_not_called()
