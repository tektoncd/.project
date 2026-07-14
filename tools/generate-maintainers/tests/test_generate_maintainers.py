#!/usr/bin/env python3
"""
Unit tests for generate_maintainers.py.

Run with:
    python3 -m pytest tools/generate-maintainers/tests/
or from the tools/generate-maintainers directory:
    python3 -m pytest tests/
"""

import textwrap
import sys
from pathlib import Path

import pytest

# Make the package importable regardless of working directory
sys.path.insert(0, str(Path(__file__).parent.parent))
from generate_maintainers import (  # noqa: E402
    HEADER,
    _union_sorted,
    build_teams,
    extract_org_teams,
    load_org_yaml,
    render_yaml,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TESTDATA = Path(__file__).parent / "testdata" / "org.yaml"


@pytest.fixture()
def org_data():
    return load_org_yaml(TESTDATA)


@pytest.fixture()
def org_teams(org_data):
    return extract_org_teams(org_data)


# ---------------------------------------------------------------------------
# _union_sorted
# ---------------------------------------------------------------------------


class TestUnionSorted:
    def test_basic_union(self):
        assert _union_sorted(["b", "a"], ["c"]) == ["a", "b", "c"]

    def test_deduplication(self):
        assert _union_sorted(["alice", "bob"], ["bob", "carol"]) == [
            "alice",
            "bob",
            "carol",
        ]

    def test_case_insensitive_sort(self):
        result = _union_sorted(["Zoe", "alice"], ["Bob"])
        assert result == ["alice", "Bob", "Zoe"]

    def test_empty_inputs(self):
        assert _union_sorted([], []) == []

    def test_one_empty(self):
        assert _union_sorted(["x"], []) == ["x"]
        assert _union_sorted([], ["y"]) == ["y"]


# ---------------------------------------------------------------------------
# extract_org_teams
# ---------------------------------------------------------------------------


class TestExtractOrgTeams:
    def test_returns_teams_dict(self, org_data):
        teams = extract_org_teams(org_data)
        assert isinstance(teams, dict)

    def test_contains_expected_keys(self, org_data):
        teams = extract_org_teams(org_data)
        assert "governing-board" in teams
        assert "pipeline.maintainers" in teams

    def test_raises_on_bad_structure(self):
        with pytest.raises(KeyError):
            extract_org_teams({})


# ---------------------------------------------------------------------------
# build_teams
# ---------------------------------------------------------------------------


class TestBuildTeams:
    def test_first_team_is_project_maintainers(self, org_teams):
        teams = build_teams(org_teams)
        assert teams[0]["name"] == "project-maintainers"

    def test_project_maintainers_from_governing_board(self, org_teams):
        teams = build_teams(org_teams)
        pm = teams[0]
        # governing-board has alice, bob, carol (no maintainers in fixture)
        assert pm["members"] == ["alice", "bob", "carol"]

    def test_project_maintainers_merges_gb_maintainers(self):
        org_teams = {
            "governing-board": {
                "members": ["alice"],
                "maintainers": ["bob"],
            }
        }
        teams = build_teams(org_teams)
        assert set(teams[0]["members"]) == {"alice", "bob"}

    def test_non_maintainer_teams_excluded(self, org_teams):
        teams = build_teams(org_teams)
        names = [t["name"] for t in teams]
        assert "pipeline-collaborators" not in names

    def test_maintainer_teams_included(self, org_teams):
        teams = build_teams(org_teams)
        names = [t["name"] for t in teams]
        assert "pipeline-maintainers" in names
        assert "triggers-maintainers" in names

    def test_team_name_uses_dash_separator(self, org_teams):
        teams = build_teams(org_teams)
        for team in teams[1:]:  # skip project-maintainers
            assert "." not in team["name"]
            assert team["name"].endswith("-maintainers")

    def test_members_union_no_overlap(self, org_teams):
        teams = build_teams(org_teams)
        pm = next(t for t in teams if t["name"] == "pipeline-maintainers")
        assert set(pm["members"]) == {"dave", "eve", "frank"}

    def test_members_union_with_overlap(self, org_teams):
        teams = build_teams(org_teams)
        tm = next(t for t in teams if t["name"] == "triggers-maintainers")
        # heidi appears in both members and maintainers — should appear once
        assert set(tm["members"]) == {"grace", "heidi", "ivan"}
        assert tm["members"].count("heidi") == 1

    def test_members_sorted_case_insensitive(self, org_teams):
        teams = build_teams(org_teams)
        for team in teams:
            lower = [m.casefold() for m in team["members"]]
            assert lower == sorted(lower), f"{team['name']} members not sorted"

    def test_empty_maintainers_team(self, org_teams):
        teams = build_teams(org_teams)
        et = next((t for t in teams if t["name"] == "empty-maintainers"), None)
        assert et is not None
        assert et["members"] == []

    def test_teams_ordered_alphabetically(self, org_teams):
        teams = build_teams(org_teams)
        # project-maintainers is always first; the rest must be sorted
        rest = [t["name"] for t in teams[1:]]
        assert rest == sorted(rest)

    def test_no_governing_board_team_skipped(self):
        """governing-board should not also appear as 'governing-board-maintainers'."""
        org_teams = {
            "governing-board": {"members": ["alice"], "maintainers": []},
        }
        teams = build_teams(org_teams)
        names = [t["name"] for t in teams]
        assert "governing-board-maintainers" not in names

    def test_missing_governing_board(self):
        """Gracefully handles org.yaml with no governing-board team."""
        teams = build_teams({})
        assert teams[0]["name"] == "project-maintainers"
        assert teams[0]["members"] == []


# ---------------------------------------------------------------------------
# render_yaml
# ---------------------------------------------------------------------------


class TestRenderYaml:
    def test_output_starts_with_header(self):
        output = render_yaml([])
        assert output.startswith(HEADER)

    def test_contains_project_id(self):
        output = render_yaml([])
        assert 'project_id: "tekton"' in output

    def test_contains_org(self):
        output = render_yaml([])
        assert 'org: "tektoncd"' in output

    def test_team_name_quoted(self):
        teams = [{"name": "my-team", "members": ["alice"]}]
        output = render_yaml(teams)
        assert '- name: "my-team"' in output

    def test_members_listed(self):
        teams = [{"name": "my-team", "members": ["alice", "bob"]}]
        output = render_yaml(teams)
        assert "          - alice" in output
        assert "          - bob" in output

    def test_ends_with_newline(self):
        output = render_yaml([])
        assert output.endswith("\n")

    def test_full_roundtrip(self, org_teams):
        teams = build_teams(org_teams)
        output = render_yaml(teams)
        # The output must be valid YAML that can be re-parsed
        import yaml

        parsed = yaml.safe_load(output)
        assert parsed["maintainers"][0]["org"] == "tektoncd"
        team_names = [t["name"] for t in parsed["maintainers"][0]["teams"]]
        assert "project-maintainers" in team_names
        assert "pipeline-maintainers" in team_names

    def test_no_trailing_spaces_on_any_line(self, org_teams):
        teams = build_teams(org_teams)
        output = render_yaml(teams)
        for lineno, line in enumerate(output.splitlines(), 1):
            assert line == line.rstrip(), (
                f"Trailing whitespace on line {lineno}: {line!r}"
            )

    def test_no_lines_with_only_whitespace(self, org_teams):
        teams = build_teams(org_teams)
        output = render_yaml(teams)
        for lineno, line in enumerate(output.splitlines(), 1):
            assert line.strip() != "" or line == "", (
                f"Line {lineno} contains only whitespace: {line!r}"
            )


# ---------------------------------------------------------------------------
# Integration: load → build → render
# ---------------------------------------------------------------------------


class TestIntegration:
    def test_end_to_end_from_fixture(self, tmp_path):
        import yaml

        data = load_org_yaml(TESTDATA)
        org_teams = extract_org_teams(data)
        teams = build_teams(org_teams)
        content = render_yaml(teams)

        out = tmp_path / "maintainers.yaml"
        out.write_text(content)

        parsed = yaml.safe_load(out.read_text())
        result_teams = parsed["maintainers"][0]["teams"]
        names = [t["name"] for t in result_teams]

        assert names[0] == "project-maintainers"
        assert "pipeline-maintainers" in names
        assert "triggers-maintainers" in names
        assert "empty-maintainers" in names
        # Non-maintainer teams must be absent
        assert "pipeline-collaborators" not in names

        # Verify member deduplication survived the full round-trip
        triggers = next(t for t in result_teams if t["name"] == "triggers-maintainers")
        assert triggers["members"].count("heidi") == 1
