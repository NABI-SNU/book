"""Re-execute the notebooks that the book build does not execute, and store their outputs.

Heavy notebooks (long training runs, large downloads, slow `pip install` cells) are
listed under `execute.exclude_patterns` in `book/_config.yml`. The build renders their
committed outputs instead of running them. This script is the way to refresh those
outputs: it executes every notebook under `tutorials/` that matches one of the patterns,
in place, with the notebook's own folder as the working directory (as in the build).

Usage:
    python ci/refresh_outputs.py            # refresh all excluded notebooks
    python ci/refresh_outputs.py --list     # only print which notebooks match
    python ci/refresh_outputs.py PATTERN    # refresh only notebooks whose path contains PATTERN

The `refresh-notebook-outputs` workflow runs this in CI, where the environment matches
the book build, and commits the result.
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path, PurePosixPath

import nbformat
import yaml
from nbclient import NotebookClient

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = REPO_ROOT / "book" / "_config.yml"
TUTORIALS_DIR = REPO_ROOT / "tutorials"
# Generous per-cell limit: these notebooks are excluded precisely because they are slow.
CELL_TIMEOUT = 1800


def excluded_notebooks() -> list[Path]:
    config = yaml.safe_load(CONFIG_FILE.read_text(encoding="utf-8"))
    patterns = config.get("execute", {}).get("exclude_patterns") or []
    matches = []
    for path in sorted(TUTORIALS_DIR.rglob("*.ipynb")):
        if ".ipynb_checkpoints" in path.parts:
            continue
        posix = PurePosixPath(path.relative_to(REPO_ROOT).as_posix())
        if any(posix.match(pattern) for pattern in patterns):
            matches.append(path)
    return matches


PROGRESS_LINE = re.compile(r"^\s*(\d+%\|.*\|.*)?\s*$")


def strip_progress_bars(notebook) -> None:
    """Drop stderr streams that only contain download/progress bars (tqdm), which render as noise."""
    for cell in notebook.cells:
        if cell.cell_type != "code":
            continue
        cell.outputs = [
            output
            for output in cell.get("outputs", [])
            if not (
                output.get("output_type") == "stream"
                and output.get("name") == "stderr"
                and all(PROGRESS_LINE.match(line) for line in re.split(r"[\r\n]", output.get("text", "")))
            )
        ]


def execute_in_place(path: Path) -> list[str]:
    raw = path.read_text(encoding="utf-8")
    notebook = nbformat.reads(raw, as_version=4)
    client = NotebookClient(
        notebook,
        timeout=CELL_TIMEOUT,
        kernel_name="python3",
        allow_errors=True,
        record_timing=False,
        resources={"metadata": {"path": str(path.parent)}},
    )
    client.execute()
    strip_progress_bars(notebook)

    errors = [
        f"{output.get('ename')}: {output.get('evalue')}"
        for cell in notebook.cells
        if cell.cell_type == "code"
        for output in cell.get("outputs", [])
        if output.get("output_type") == "error"
    ]
    # Match the repository's existing notebook formatting to keep diffs small.
    payload = json.loads(nbformat.writes(notebook))
    path.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("filter", nargs="?", default="", help="only refresh notebooks whose path contains this text")
    parser.add_argument("--list", action="store_true", help="print matching notebooks and exit")
    args = parser.parse_args()

    notebooks = [p for p in excluded_notebooks() if args.filter in p.as_posix()]
    if not notebooks:
        print("No notebooks match the exclude patterns in book/_config.yml.")
        return 1

    for path in notebooks:
        rel = path.relative_to(REPO_ROOT)
        if args.list:
            print(rel)
            continue
        start = time.time()
        print(f"Executing {rel} ...", flush=True)
        errors = execute_in_place(path)
        print(f"  done in {time.time() - start:.0f}s, {len(errors)} cell error(s)", flush=True)
        for error in errors:
            print(f"    {error[:200]}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
