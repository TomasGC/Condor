"""Cut a Condor release.

A release is a commit that is not on main: main with every internal reference
(TomasGC/Condor/.github/...@main) rewritten to the exact tag. A caller pinned to the tag, or to the release
commit, then runs workflows and actions from the same release; nothing floats on main.
The moving tag of the major version (v1) follows the newest release of that major version.

    python .github/scripts/release.py 1.0.0 --dry-run
    python .github/scripts/release.py 1.0.0 --push
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
RELEASE_BRANCH = "main"
VERSION_PATTERN = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
TAG_PATTERN = re.compile(r"^refs/tags/v(\d+)\.(\d+)\.(\d+)$")
INTERNAL_REF = re.compile(r"TomasGC/Condor/\.github/(?:actions|workflows)/[A-Za-z0-9_./-]+@([A-Za-z0-9_./-]+)")
MAIN_REF = re.compile(r"(TomasGC/Condor/\.github/(?:actions|workflows)/[A-Za-z0-9_./-]+)@main(?![A-Za-z0-9_./-])")


def parse_version(text: str) -> tuple[int, int, int]:
    """Return (major, minor, patch) of a version written 1.2.3."""
    match = VERSION_PATTERN.match(text)
    if match is None:
        raise ValueError(f"version must look like 1.2.3 (got {text!r})")
    major, minor, patch = (int(part) for part in match.groups())
    return major, minor, patch


def rewrite_refs(text: str, tag: str) -> tuple[str, int]:
    """Point every internal reference on main at the tag; return the new text and the number of references."""
    return MAIN_REF.subn(lambda match: f"{match.group(1)}@{tag}", text)


def workflow_files(root: Path) -> list[Path]:
    return sorted((root / ".github").rglob("*.yml"))


def find_foreign_refs(root: Path) -> list[str]:
    """Internal references that are not on main (a branch under test, a sha): a release must not carry them."""
    found = []
    for path in workflow_files(root):
        for line_number, line in enumerate(path.read_bytes().decode("utf-8").splitlines(), start=1):
            for match in INTERNAL_REF.finditer(line):
                if match.group(1) != RELEASE_BRANCH:
                    found.append(f"{path.relative_to(root).as_posix()}:{line_number}: @{match.group(1)}")
    return found


def rewrite_tree(root: Path, tag: str, write: bool = True) -> list[Path]:
    """Rewrite the references of every workflow and action under .github/; return the files that change."""
    changed = []
    for path in workflow_files(root):
        text = path.read_bytes().decode("utf-8")
        new_text, count = rewrite_refs(text, tag)
        if count:
            changed.append(path)
            if write:
                path.write_bytes(new_text.encode("utf-8"))
    return changed


def highest_release(tag_refs: list[str], major: int) -> tuple[int, int, int] | None:
    """Newest released version of a major version, from `refs/tags/vX.Y.Z` lines; None when there is none."""
    versions = []
    for ref in tag_refs:
        match = TAG_PATTERN.match(ref)
        if match and int(match.group(1)) == major:
            versions.append(tuple(int(part) for part in match.groups()))
    return max(versions) if versions else None  # type: ignore[return-value]


def git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def remote_tag_refs(root: Path, remote: str) -> list[str]:
    output = git(root, "ls-remote", "--tags", remote, "refs/tags/v*")
    return [line.split("\t")[1] for line in output.splitlines() if "\t" in line]


def check_ready(root: Path, remote: str, tag: str) -> list[str]:
    """Refuse a release from anything but a clean main that equals the remote's, with an unused tag."""
    if git(root, "status", "--porcelain"):
        raise RuntimeError("the working tree is not clean")
    if git(root, "branch", "--show-current") != RELEASE_BRANCH:
        raise RuntimeError(f"a release is cut from {RELEASE_BRANCH}")
    git(root, "fetch", remote, RELEASE_BRANCH)
    if git(root, "rev-parse", "HEAD") != git(root, "rev-parse", f"{remote}/{RELEASE_BRANCH}"):
        raise RuntimeError(f"{RELEASE_BRANCH} is not at {remote}/{RELEASE_BRANCH}")
    tag_refs = remote_tag_refs(root, remote)
    if f"refs/tags/{tag}" in tag_refs or git(root, "tag", "--list", tag):
        raise RuntimeError(f"the tag {tag} already exists")
    foreign = find_foreign_refs(root)
    if foreign:
        raise RuntimeError("internal references not on main:\n  " + "\n  ".join(foreign))
    return tag_refs


def release(root: Path, version: str, remote: str = "origin", push: bool = False, dry_run: bool = False) -> str:
    major, minor, patch = parse_version(version)
    tag, major_tag = f"v{version}", f"v{major}"
    tag_refs = check_ready(root, remote, tag)
    if dry_run:
        changed = rewrite_tree(root, tag, write=False)
        print(f"{tag}: would rewrite {len(changed)} file(s)")
        return tag

    newest = highest_release(tag_refs, major)
    moves_major = newest is None or (major, minor, patch) > newest
    git(root, "switch", "--detach")
    try:
        rewrite_tree(root, tag)
        git(root, "commit", "--all", "--message", f"chore: release {tag}")
        git(root, "tag", tag)
        if moves_major:
            git(root, "tag", "--force", major_tag)
    finally:
        git(root, "switch", RELEASE_BRANCH)
    if push:
        git(root, "push", remote, f"refs/tags/{tag}")
        if moves_major:
            git(root, "push", "--force", remote, f"refs/tags/{major_tag}")
    print(f"{tag}: released{' and pushed' if push else ' locally'}; {major_tag} {'moved' if moves_major else 'kept'}")
    return tag


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Cut a Condor release")
    parser.add_argument("version", help="the new version, written 1.2.3")
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--push", action="store_true", help="push the tag (and the moved major tag)")
    parser.add_argument("--dry-run", action="store_true", help="check and count the files to rewrite, change nothing")
    args = parser.parse_args(argv)
    try:
        release(REPOSITORY_ROOT, args.version, args.remote, args.push, args.dry_run)
    except (ValueError, RuntimeError) as error:
        print(f"::error::{error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
