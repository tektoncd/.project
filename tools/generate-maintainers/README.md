# generate-maintainers

Generates [`maintainers.yaml`](../../maintainers.yaml) from the canonical
[`org.yaml`](https://raw.githubusercontent.com/tektoncd/community/refs/heads/main/org/org.yaml)
file maintained in [tektoncd/community](https://github.com/tektoncd/community).

## Mapping rules

| `org.yaml` team | `maintainers.yaml` team | Members |
|---|---|---|
| `governing-board` | `project-maintainers` | union of `members` + `maintainers` |
| `<project>.maintainers` | `<project>-maintainers` | union of `members` + `maintainers` |

Teams that do not end in `.maintainers` (e.g. `*.collaborators`, `*.admins`,
`tekton-vmt`) are ignored.

## Requirements

- Python ≥ 3.10
- [PyYAML](https://pypi.org/project/PyYAML/)

```bash
pip install pyyaml
```

Or use a virtual environment (recommended on systems with a managed Python):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pyyaml
```

## Usage

Run from **any directory** — the script resolves the output path relative to
its own location:

```bash
python3 tools/generate-maintainers/generate_maintainers.py
```

This writes (or overwrites) `maintainers.yaml` at the repository root.

To write to a different path:

```bash
python3 tools/generate-maintainers/generate_maintainers.py /tmp/preview.yaml
```

## Running the tests

From the repository root:

```bash
python3 -m pytest tools/generate-maintainers/tests/ -v
```

Or from the tool directory:

```bash
cd tools/generate-maintainers
python3 -m pytest tests/ -v
```

### Test layout

```
tools/generate-maintainers/
├── generate_maintainers.py       # main script
├── README.md                     # this file
└── tests/
    ├── test_generate_maintainers.py   # unit + integration tests
    └── testdata/
        └── org.yaml                   # minimal org.yaml fixture
```

### What is tested

| Area | Tests |
|---|---|
| `_union_sorted` | deduplication, case-insensitive sort, empty inputs |
| `extract_org_teams` | correct key extraction, error on bad structure |
| `build_teams` | project-maintainers from GB, name mapping (`.` → `-`), member union/dedup, alphabetical order, non-maintainer teams excluded, missing GB gracefully handled |
| `render_yaml` | header presence, YAML validity, no trailing whitespace, trailing newline |
| Integration | full fixture load → build → render → re-parse round-trip |
