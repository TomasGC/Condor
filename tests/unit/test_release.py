import pytest
import release

TAG = "v1.2.3"


@pytest.mark.parametrize("text, expected", [("1.2.3", (1, 2, 3)), ("0.0.1", (0, 0, 1)), ("10.20.30", (10, 20, 30))])
def test_parse_version_accepts_three_numbers(text, expected):
    assert release.parse_version(text) == expected


@pytest.mark.parametrize("text", ["1.2", "v1.2.3", "1.2.3-rc1", "1.2.x", "", "1.2.3 ", "1.2.3\n; rm -rf /"])
def test_parse_version_rejects_anything_else(text):
    with pytest.raises(ValueError, match="version must look like 1.2.3"):
        release.parse_version(text)


def test_rewrite_refs_points_actions_and_workflows_at_the_tag():
    text = (
        "      - uses: TomasGC/Condor/.github/actions/install-ffmpeg@main\n"
        "    uses: TomasGC/Condor/.github/workflows/kotlin-push-ci.yml@main\n"
    )
    new_text, count = release.rewrite_refs(text, TAG)
    assert count == 2
    assert "install-ffmpeg@v1.2.3\n" in new_text
    assert "kotlin-push-ci.yml@v1.2.3\n" in new_text
    assert "@main" not in new_text


def test_rewrite_refs_leaves_other_references_alone():
    text = (
        "uses: actions/checkout@v4\n"
        "uses: someone/Else/.github/actions/x@main\n"
        "uses: TomasGC/Condor/.github/actions/x@main-experiment\n"
        "uses: ./.github/workflows/python-pytest.yml\n"
    )
    assert release.rewrite_refs(text, TAG) == (text, 0)


def test_rewrite_refs_is_idempotent():
    once, _ = release.rewrite_refs("uses: TomasGC/Condor/.github/actions/x@main\n", TAG)
    assert release.rewrite_refs(once, TAG) == (once, 0)


def test_rewrite_tree_changes_only_files_under_github(tmp_path):
    workflow = tmp_path / ".github" / "workflows" / "a.yml"
    action = tmp_path / ".github" / "actions" / "b" / "action.yml"
    readme = tmp_path / "README.md"
    fixture = tmp_path / "tests" / "fixtures" / "c.yml"
    line = "uses: TomasGC/Condor/.github/actions/x@main\n"
    for path in (workflow, action, readme, fixture):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(line, encoding="utf-8")

    changed = release.rewrite_tree(tmp_path, TAG)

    assert changed == sorted([action, workflow])
    assert "@v1.2.3" in workflow.read_text(encoding="utf-8")
    assert "@v1.2.3" in action.read_text(encoding="utf-8")
    assert readme.read_text(encoding="utf-8") == line
    assert fixture.read_text(encoding="utf-8") == line


def test_rewrite_tree_keeps_line_endings(tmp_path):
    path = tmp_path / ".github" / "workflows" / "a.yml"
    path.parent.mkdir(parents=True)
    path.write_bytes(b"uses: TomasGC/Condor/.github/actions/x@main\r\nname: y\r\n")
    release.rewrite_tree(tmp_path, TAG)
    assert path.read_bytes() == b"uses: TomasGC/Condor/.github/actions/x@v1.2.3\r\nname: y\r\n"


def test_rewrite_tree_dry_run_changes_nothing(tmp_path):
    path = tmp_path / ".github" / "workflows" / "a.yml"
    path.parent.mkdir(parents=True)
    path.write_text("uses: TomasGC/Condor/.github/actions/x@main\n", encoding="utf-8")
    assert release.rewrite_tree(tmp_path, TAG, write=False) == [path]
    assert path.read_text(encoding="utf-8").endswith("@main\n")


def test_find_foreign_refs_reports_a_branch_under_test_and_a_sha(tmp_path):
    path = tmp_path / ".github" / "workflows" / "a.yml"
    path.parent.mkdir(parents=True)
    path.write_text(
        "uses: TomasGC/Condor/.github/actions/x@main\n"
        "uses: TomasGC/Condor/.github/actions/y@feature/27-versioned-releases\n"
        "uses: TomasGC/Condor/.github/workflows/z.yml@0123abc\n",
        encoding="utf-8",
    )
    assert release.find_foreign_refs(tmp_path) == [
        ".github/workflows/a.yml:2: @feature/27-versioned-releases",
        ".github/workflows/a.yml:3: @0123abc",
    ]


def test_highest_release_ignores_other_majors_and_non_release_tags():
    refs = ["refs/tags/v1.0.0", "refs/tags/v1.4.2", "refs/tags/v1.10.0", "refs/tags/v2.0.0", "refs/tags/v1", "refs/tags/v1.2"]
    assert release.highest_release(refs, 1) == (1, 10, 0)
    assert release.highest_release(refs, 2) == (2, 0, 0)
    assert release.highest_release(refs, 3) is None
