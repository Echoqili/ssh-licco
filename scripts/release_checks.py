"""Release checks shared by CI and local recovery. Uses only the standard library."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


def validate_tag(tag: str, version: str) -> str:
    if not re.fullmatch(r"v\d+\.\d+\.\d+", tag) or tag != f"v{version}":
        raise ValueError(f"Expected immutable release tag v{version}, got {tag!r}")
    return version


def fetch_pypi(version: str) -> dict | None:
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        raise ValueError("Invalid version")
    for attempt in range(3):
        try:
            with urlopen(f"https://pypi.org/pypi/ssh-licco/{version}/json", timeout=20) as response:
                data = json.loads(response.read())
            if not isinstance(data, dict) or not isinstance(data.get("urls"), list):
                raise ValueError("Unexpected PyPI metadata; refusing to assume version is absent")
            if any(not isinstance(row.get("filename"), str) for row in data["urls"]):
                raise ValueError("Invalid PyPI file metadata")
            return data
        except HTTPError as error:
            if error.code == 404:
                return None
            if error.code not in (429, 500, 502, 503, 504):
                raise RuntimeError(f"PyPI query failed: HTTP {error.code}") from error
        except (URLError, TimeoutError) as error:
            if attempt == 2:
                raise RuntimeError(
                    "PyPI is unavailable; publication has not been authorized"
                ) from error
        if attempt < 2:
            time.sleep(attempt + 1)
    raise RuntimeError("PyPI query failed after retries; refusing to upload")


def distributions(dist: Path, version: str) -> list[Path]:
    expected = [
        dist / f"ssh_licco-{version}-py3-none-any.whl",
        dist / f"ssh_licco-{version}.tar.gz",
    ]
    if not all(path.is_file() for path in expected):
        raise ValueError("Build must produce the versioned wheel and source distribution")
    return expected


def stage_missing(dist: Path, staging: Path, version: str) -> int:
    files = distributions(dist, version)
    metadata = fetch_pypi(version)
    published = {row["filename"] for row in metadata["urls"]} if metadata else set()
    staging.mkdir(parents=True, exist_ok=True)
    if any(staging.iterdir()):
        raise ValueError("Upload staging directory must be empty")
    missing = [file for file in files if file.name not in published]
    for file in missing:
        shutil.copy2(file, staging / file.name)
    return len(missing)


def verify_public(dist: Path, version: str, attempts: int = 6) -> None:
    expected = {path.name for path in distributions(dist, version)}
    for attempt in range(attempts):
        metadata = fetch_pypi(version)
        published = {row["filename"] for row in metadata["urls"]} if metadata else set()
        if expected <= published:
            return
        if attempt + 1 < attempts:
            time.sleep(5)
    raise RuntimeError("PyPI does not contain both release distributions")


def verify_installed(source: Path, version: str) -> None:
    if importlib.metadata.version("ssh-licco") != version:
        raise ValueError("Installed PyPI version does not match release tag")
    spec = importlib.util.find_spec("ssh_mcp")
    if spec is None or spec.origin is None:
        raise ValueError("Installed SSH MCP package is missing")
    installed = Path(spec.origin).parent.resolve()
    package = (source / "ssh_mcp").resolve()
    if installed == package:
        raise ValueError("Verification must import the installed wheel outside the source tree")
    for path in package.rglob("*.py"):
        other = installed / path.relative_to(package)
        if not other.is_file() or path.read_bytes().replace(
            b"\r\n", b"\n"
        ) != other.read_bytes().replace(b"\r\n", b"\n"):
            raise ValueError(
                f"Published code differs from release tag: {path.relative_to(package)}"
            )


def output(name: str, value: str) -> None:
    print(f"{name}={value}")
    if os.getenv("GITHUB_OUTPUT"):
        with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as stream:
            stream.write(f"{name}={value}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=["plan", "check-tag", "stage", "verify", "installed", "checksums"]
    )
    parser.add_argument("--tag", default=os.getenv("RELEASE_TAG", ""))
    parser.add_argument("--source", type=Path, default=Path.cwd())
    parser.add_argument("--dist", type=Path, default=Path("dist"))
    parser.add_argument("--staging", type=Path, default=Path("publish-dist"))
    args = parser.parse_args()
    if args.action == "plan":
        if not re.fullmatch(r"v\d+\.\d+\.\d+", args.tag):
            raise ValueError("Select an existing vX.Y.Z tag; branches cannot be published")
        sha = subprocess.check_output(
            ["git", "rev-parse", "--verify", f"refs/tags/{args.tag}^{{commit}}"],
            cwd=args.source,
            text=True,
        ).strip()
        if not re.fullmatch(r"[0-9a-f]{40,64}", sha):
            raise ValueError("Invalid tag commit")
        output("tag", args.tag)
        output("sha", sha)
        output("version", args.tag[1:])
        return
    version = (args.source / "VERSION").read_text(encoding="utf-8").strip()
    validate_tag(args.tag, version)
    if args.action == "check-tag":
        output("version", version)
    elif args.action == "stage":
        count = stage_missing(args.dist, args.staging, version)
        output("upload", str(count > 0).lower())
        output("missing_files", str(count))
    elif args.action == "verify":
        verify_public(args.dist, version)
    elif args.action == "installed":
        verify_installed(args.source, version)
        print("Published Python sources match the immutable release tag")
    elif args.action == "checksums":
        files = sorted(
            path for path in args.dist.iterdir() if path.is_file() and path.name != "SHA256SUMS"
        )
        if not files:
            raise ValueError("No release assets found")
        text = "".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in files)
        (args.dist / "SHA256SUMS").write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
