#!/usr/bin/env python3
"""
Generate maintainers.yaml from tektoncd/community org.yaml.

Rules:
  - "project-maintainers" team = union of members + maintainers of the
    "governing-board" team in org.yaml.
  - For each "<project>.maintainers" team in org.yaml, create a
    "<project>-maintainers" team in maintainers.yaml whose members are
    the union of all members + maintainers listed under that org.yaml team.

Usage:
    python3 generate_maintainers.py [OUTPUT_PATH]

    OUTPUT_PATH defaults to "../../maintainers.yaml" (the repo root file).
"""

import sys
import urllib.request
from pathlib import Path

import yaml

ORG_YAML_URL = (
    "https://raw.githubusercontent.com/tektoncd/community"
    "/refs/heads/main/org/org.yaml"
)

# Path from this script to the repo-root maintainers.yaml
_DEFAULT_OUTPUT = Path(__file__).parent.parent.parent / "maintainers.yaml"

HEADER = """\
# Maintainer roster for Tekton
# Documentation: https://github.com/cncf/automation/tree/main/utilities/dot-project


#  Maintainers: Please connect your GitHub handle to your LFID on openprofile.dev
#  to enable automatic access to CNCF resources. The system will use your primary
#  email address for setup.
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _union_sorted(a: list, b: list) -> list:
    """Return the sorted (case-insensitive) union of two lists."""
    return sorted(set(a) | set(b), key=str.casefold)


# ---------------------------------------------------------------------------
# Core logic (pure functions, no I/O — easy to unit-test)
# ---------------------------------------------------------------------------


def extract_org_teams(data: dict) -> dict:
    """Return the teams dict from a parsed org.yaml structure."""
    return data["orgs"]["tektoncd"]["teams"]


def build_teams(org_teams: dict) -> list[dict]:
    """
    Build the list of maintainer team dicts for maintainers.yaml.

    Parameters
    ----------
    org_teams:
        The value of ``data["orgs"]["tektoncd"]["teams"]`` from org.yaml.

    Returns
    -------
    list of dicts with keys ``name`` and ``members``.
    """
    teams: list[dict] = []

    # project-maintainers = union of governing-board members + maintainers
    gb = org_teams.get("governing-board", {})
    gb_members = _union_sorted(gb.get("members", []), gb.get("maintainers", []))
    teams.append({"name": "project-maintainers", "members": gb_members})

    # <project>.maintainers -> <project>-maintainers
    for team_name in sorted(org_teams.keys()):
        if not team_name.endswith(".maintainers"):
            continue
        project = team_name[: -len(".maintainers")]
        t = org_teams[team_name]
        combined = _union_sorted(t.get("members", []), t.get("maintainers", []))
        teams.append({"name": f"{project}-maintainers", "members": combined})

    return teams


def render_yaml(teams: list[dict]) -> str:
    """
    Render the maintainers.yaml content as a string.

    The output is hand-formatted (not via yaml.dump) to preserve the
    comment header and the exact style expected by the CNCF tooling.
    """
    lines: list[str] = [HEADER]
    lines.append("maintainers:")
    lines.append('  - project_id: "tekton"')
    lines.append('    org: "tektoncd"')
    lines.append("    teams:")
    for team in teams:
        lines.append(f'      - name: "{team["name"]}"')
        lines.append("        members:")
        for member in team["members"]:
            lines.append(f"          - {member}")
    lines.append("")  # trailing newline
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------


def fetch_org_yaml(url: str) -> dict:
    """Fetch and parse org.yaml from *url*."""
    with urllib.request.urlopen(url) as response:
        return yaml.safe_load(response.read())


def load_org_yaml(path: str | Path) -> dict:
    """Load and parse org.yaml from a local *path*."""
    with open(path) as fh:
        return yaml.safe_load(fh)


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------


def main() -> None:
    output_path = Path(sys.argv[1]) if len(sys.argv) > 1 else _DEFAULT_OUTPUT

    print(f"Fetching {ORG_YAML_URL} …", flush=True)
    data = fetch_org_yaml(ORG_YAML_URL)
    org_teams = extract_org_teams(data)

    maintainers_count = sum(1 for t in org_teams if t.endswith(".maintainers"))
    print(
        f"Found {len(org_teams)} teams; {maintainers_count} *.maintainers teams.",
        flush=True,
    )

    teams = build_teams(org_teams)
    content = render_yaml(teams)

    with open(output_path, "w") as fh:
        fh.write(content)

    print(f"Written {output_path} with {len(teams)} teams.")
    for team in teams:
        print(f"  {team['name']}: {len(team['members'])} members")


if __name__ == "__main__":
    main()
