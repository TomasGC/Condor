import subprocess
from pathlib import Path

import pytest
import release

LINE = "    uses: TomasGC/Condor/.github/workflows/kotlin-push-ci.yml@main\n"


def run(cwd: Path, *args: str) -> str:
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=True)
    return result.stdout.strip()


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A clone of a bare 'origin' holding one workflow that calls Condor on main."""
    for name, value in (("NAME", "Test"), ("EMAIL", "test@example.invalid")):
        monkeypatch.setenv(f"GIT_AUTHOR_{name}", value)
        monkeypatch.setenv(f"GIT_COMMITTER_{name}", value)
    origin = tmp_path / "origin.git"
    run(tmp_path, "git", "init", "--bare", "--initial-branch=main", str(origin))
    work = tmp_path / "work"
    run(tmp_path, "git", "clone", str(origin), str(work))
    workflow = work / ".github" / "workflows" / "a.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text(LINE, encoding="utf-8")
    (work / "README.md").write_text(LINE, encoding="utf-8")
    run(work, "git", "add", ".")
    run(work, "git", "commit", "--message", "first")
    run(work, "git", "push", "origin", "main")
    return work


def test_release_commits_off_main_and_tags_it(repo):
    main_before = run(repo, "git", "rev-parse", "main")

    release.release(repo, "1.0.0")

    assert run(repo, "git", "branch", "--show-current") == "main"
    assert run(repo, "git", "rev-parse", "main") == main_before
    assert run(repo, "git", "rev-parse", "v1") == run(repo, "git", "rev-parse", "v1.0.0")
    released = run(repo, "git", "show", "v1.0.0:.github/workflows/a.yml")
    assert "kotlin-push-ci.yml@v1.0.0" in released
    assert "@main" not in released
    assert run(repo, "git", "show", "v1.0.0:README.md") == LINE.strip()
    assert (repo / ".github" / "workflows" / "a.yml").read_text(encoding="utf-8") == LINE


def test_release_pushes_the_tags_and_moves_the_major_tag(repo):
    release.release(repo, "1.0.0", push=True)
    release.release(repo, "1.1.0", push=True)

    remote = run(repo, "git", "ls-remote", "--tags", "origin")
    refs = {line.split("\t")[1]: line.split("\t")[0] for line in remote.splitlines()}
    assert set(refs) == {"refs/tags/v1.0.0", "refs/tags/v1.1.0", "refs/tags/v1"}
    assert refs["refs/tags/v1"] == refs["refs/tags/v1.1.0"] != refs["refs/tags/v1.0.0"]


def test_an_older_patch_does_not_move_the_major_tag(repo):
    release.release(repo, "1.1.0", push=True)
    release.release(repo, "1.0.5", push=True)

    remote = run(repo, "git", "ls-remote", "--tags", "origin")
    refs = {line.split("\t")[1]: line.split("\t")[0] for line in remote.splitlines()}
    assert refs["refs/tags/v1"] == refs["refs/tags/v1.1.0"]


def test_release_refuses_a_tag_that_exists(repo):
    release.release(repo, "1.0.0", push=True)
    with pytest.raises(RuntimeError, match="already exists"):
        release.release(repo, "1.0.0")


def test_release_refuses_a_dirty_tree(repo):
    (repo / "README.md").write_text("changed\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="not clean"):
        release.release(repo, "1.0.0")


def test_release_refuses_a_branch_other_than_main(repo):
    run(repo, "git", "switch", "--create", "feature/1-x")
    with pytest.raises(RuntimeError, match="cut from main"):
        release.release(repo, "1.0.0")


def test_release_refuses_a_main_behind_or_ahead_of_the_remote(repo):
    (repo / "extra.txt").write_text("x\n", encoding="utf-8")
    run(repo, "git", "add", ".")
    run(repo, "git", "commit", "--message", "unpushed")
    with pytest.raises(RuntimeError, match="not at origin/main"):
        release.release(repo, "1.0.0")


def test_release_refuses_a_reference_to_a_branch_under_test(repo):
    workflow = repo / ".github" / "workflows" / "a.yml"
    workflow.write_text(LINE.replace("@main", "@feature/27-x"), encoding="utf-8")
    run(repo, "git", "commit", "--all", "--message", "under test")
    run(repo, "git", "push", "origin", "main")
    with pytest.raises(RuntimeError, match="not on main"):
        release.release(repo, "1.0.0")


def test_dry_run_changes_nothing(repo):
    release.release(repo, "1.0.0", dry_run=True)
    assert run(repo, "git", "tag", "--list") == ""
    assert run(repo, "git", "status", "--porcelain") == ""


def test_main_reports_a_bad_version_as_an_error(capsys):
    assert release.main(["1.0"]) == 1
    assert "::error::version must look like 1.2.3" in capsys.readouterr().err
