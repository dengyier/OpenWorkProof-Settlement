#!/usr/bin/env python3
"""Fetch the pinned Core image inputs from public repositories, checking hashes."""

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import quote


def read_url(url, byte_range=None):
    if not url.startswith("https://"):
        raise ValueError("Runtime inputs require HTTPS")
    argv = [
        "curl", "--fail", "--silent", "--show-error", "--location",
        "--proto", "=https", "--proto-redir", "=https", "--retry", "2",
        "--retry-all-errors", "--max-time", "45", "--max-filesize", str(64 * 1024 * 1024),
    ]
    if byte_range is not None:
        argv.extend(["--range", f"{byte_range[0]}-{byte_range[1]}"])
    data = subprocess.run([*argv, url], check=True, capture_output=True).stdout
    if len(data) > 64 * 1024 * 1024:
        raise ValueError("Runtime input exceeds download limit")
    return data


def download(url, destination, expected, size):
    if type(size) is not int or not 0 < size <= 64 * 1024 * 1024:
        raise ValueError("Invalid runtime input size")
    if size > 1024 * 1024:
        pieces = []
        for start in range(0, size, 1024 * 1024):
            end = min(size - 1, start + 1024 * 1024 - 1)
            piece = read_url(url, byte_range=(start, end))
            if len(piece) != end - start + 1:
                raise ValueError("Server did not respect bounded byte range")
            pieces.append(piece)
        data = b"".join(pieces)
    else:
        data = read_url(url)
    if len(data) != size:
        raise ValueError("Runtime input size mismatch")
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError(f"SHA-256 mismatch: {destination.name}")
    destination.write_bytes(data)
    print(f"Verified {destination.name}", flush=True)


def wheel_requirements(text):
    rows = []
    for line in text.replace("\\\n", " ").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        match = re.fullmatch(r"([a-zA-Z0-9_.-]+)==([a-zA-Z0-9_.+-]+)\s+--hash=sha256:([0-9a-f]{64})\s*", line)
        if not match:
            raise ValueError("Expected an exact version and one locked wheel hash")
        rows.append(match.groups())
    if not rows:
        raise ValueError("Empty wheel hash lock")
    return rows


def snapshot_location(package, version, architecture):
    metadata = json.loads(read_url(f"https://snapshot.debian.org/mr/binary/{quote(package, safe='')}/{quote(version, safe='')}/binfiles?fileinfo=1"))
    matches = [row["hash"] for row in metadata["result"] if row["architecture"] == architecture]
    if len(matches) != 1 or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", matches[0]):
        raise ValueError(f"Locked snapshot architecture unavailable or ambiguous: {package}=={version} ({architecture})")
    # Snapshot's SHA-1 address locates the file; the frozen SHA-256 still authorizes its bytes.
    sizes = {row["size"] for row in metadata["fileinfo"][matches[0]]}
    if len(sizes) != 1:
        raise ValueError("Ambiguous snapshot input size")
    return "https://snapshot.debian.org/file/" + matches[0], sizes.pop()


def fetch_inputs(core, output):
    output.mkdir(parents=True, exist_ok=False)
    wheels, debs = output / "wheels", output / "debs"
    wheels.mkdir()
    debs.mkdir()
    images = core / "supply-chain" / "images"
    requirements = {}
    for role in ("execution", "trusted-helper"):
        for package, version, digest in wheel_requirements((images / role / "requirements.lock").read_text()):
            requirements[digest] = (package, version)
    jobs, wheel_rows = [], []
    for digest, (package, version) in sorted(requirements.items()):
        metadata = json.loads(read_url(f"https://pypi.org/pypi/{package}/{version}/json"))
        matches = [item for item in metadata["urls"] if item["digests"]["sha256"] == digest and item["filename"].endswith(".whl")]
        if len(matches) != 1:
            raise ValueError(f"Locked wheel unavailable: {package}=={version}; do not substitute another version")
        item = matches[0]
        name = item["filename"]
        if Path(name).name != name or not item["url"].startswith("https://files.pythonhosted.org/"):
            raise ValueError("Unsafe PyPI wheel location")
        wheel_rows.append((digest, name))
        jobs.append((item["url"], wheels / name, digest, item["size"]))
    deb_rows = []
    for line in (images / "trusted-helper" / "debian-packages.lock").read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        digest, name, package, version, architecture = line.split("\t")
        if not re.fullmatch(r"[0-9a-f]{64}", digest) or Path(name).name != name:
            raise ValueError("Invalid Debian package lock")
        deb_rows.append((digest, name, package, version, architecture))
    with ThreadPoolExecutor(max_workers=4) as executor:
        def deb_job(row):
            url, size = snapshot_location(*row[2:])
            return url, debs / row[1], row[0], size
        jobs.extend(executor.map(deb_job, deb_rows))
        list(executor.map(lambda job: download(*job), jobs))
    for directory, rows in ((wheels, wheel_rows), (debs, [(row[0], row[1]) for row in deb_rows])):
        (directory / "SHA256SUMS").write_text("".join(f"{digest}  {name}\n" for digest, name in rows))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="Fresh output directory; never overwrites existing inputs")
    args = parser.parse_args()
    fetch_inputs(args.core, args.output)
