import json
import hashlib
import re
import shutil
import sys
from copy import deepcopy
from pathlib import Path

import yaml
from bs4 import BeautifulSoup


ROLE = sys.argv[1]
REPO_ROOT = Path(".")
BOOK_DIR = REPO_ROOT / "book"
SOURCE_TUTORIALS_DIR = REPO_ROOT / "tutorials"
BOOK_TUTORIALS_DIR = BOOK_DIR / "tutorials"
MATERIALS_FILE = SOURCE_TUTORIALS_DIR / "materials.yml"


def notebook_file_slug(path: Path) -> str:
    return path.with_suffix("").as_posix()


def reset_staged_tutorials() -> None:
    if BOOK_TUTORIALS_DIR.is_symlink() or BOOK_TUTORIALS_DIR.is_file():
        BOOK_TUTORIALS_DIR.unlink()
    elif BOOK_TUTORIALS_DIR.exists():
        shutil.rmtree(BOOK_TUTORIALS_DIR)
    BOOK_TUTORIALS_DIR.mkdir(parents=True, exist_ok=True)


def display_part_label(part: str) -> str:
    return part.replace("_", " ")


def stage_material(material: dict) -> Path:
    source_dir = SOURCE_TUTORIALS_DIR / material["slug"]
    target_dir = BOOK_TUTORIALS_DIR / material["slug"]
    shutil.copytree(source_dir, target_dir, dirs_exist_ok=True)
    return target_dir


def stage_shared_assets() -> None:
    source_static_dir = SOURCE_TUTORIALS_DIR / "static"
    target_static_dir = BOOK_TUTORIALS_DIR / "static"
    if source_static_dir.exists():
        shutil.copytree(source_static_dir, target_static_dir, dirs_exist_ok=True)


def preprocess_notebook(path: Path) -> None:
    content = json.loads(path.read_text(encoding="utf-8"))
    content = open_links_in_new_tabs(content)
    content = change_video_widths(content)
    content = link_hidden_cells(content)
    content = normalize_markdown_structure(content)
    content = ensure_cell_ids(content, path)
    path.write_text(json.dumps(content, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def open_links_in_new_tabs(content: dict) -> dict:
    cells = content.get("cells", [])
    if not cells:
        return content

    first_source = cells[0].get("source", [])
    if not first_source:
        return content

    parsed_html = BeautifulSoup(first_source[0], "html.parser")
    for anchor in parsed_html.find_all("a"):
        anchor["target"] = "_blank"
    first_source[0] = str(parsed_html)
    return content


def link_hidden_cells(content: dict) -> dict:
    new_cells = []
    header_level = 1

    for cell in content.get("cells", []):
        updated_cell = deepcopy(cell)
        source_lines = updated_cell.get("source", [])
        joined_source = "".join(source_lines)

        if source_lines:
            first_line = source_lines[0]
            if updated_cell.get("cell_type") == "markdown" and first_line.startswith("#"):
                header_level = first_line.count("#")
            elif (
                updated_cell.get("cell_type") == "markdown"
                and first_line.startswith("---")
                and len(source_lines) > 1
                and source_lines[1].startswith("#")
            ):
                header_level = source_lines[1].count("#")

        if source_lines and ("@title" in source_lines[0] or "@markdown" in joined_source):
            metadata = updated_cell.setdefault("metadata", {})
            tags = metadata.setdefault("tags", [])
            input_tag = "remove-input" if ("YouTubeVideo" in joined_source or "IFrame" in joined_source) else "hide-input"
            if input_tag not in tags:
                tags.append(input_tag)

            title_line = source_lines[0]
            if "@title" in title_line:
                title_text = title_line.split("@title", 1)[1].strip()
                if title_text:
                    new_cells.append(
                        {
                            "cell_type": "markdown",
                            "metadata": {"generated_by": "ci.generate_book"},
                            "source": ["#" * (header_level + 1) + f" {title_text}"],
                        }
                    )

            markdown_lines = []
            for line in source_lines:
                if "@markdown" in line:
                    markdown_text = line.split("@markdown", 1)[1].strip()
                    if markdown_text:
                        markdown_lines.append(markdown_text)
            for markdown_text in markdown_lines:
                new_cells.append(
                    {
                        "cell_type": "markdown",
                        "metadata": {"generated_by": "ci.generate_book"},
                        "source": [markdown_text],
                    }
                )

        new_cells.append(updated_cell)

    content["cells"] = new_cells
    return content


def change_video_widths(content: dict) -> dict:
    for cell in content.get("cells", []):
        joined = "".join(cell.get("source", []))
        if "YouTubeVideo" not in joined:
            continue
        for idx, source_line in enumerate(cell["source"]):
            source_line = source_line.replace("854", "730")
            source_line = source_line.replace("480", "410")
            cell["source"][idx] = source_line
    return content


HEADING_RE = re.compile(r"^(#{1,6})(\s+.*)$")
ANCHOR_RE = re.compile(r"^\s*<a\s+name=['\"]([^'\"]+)['\"]\s*>\s*</a>\s*$")


def normalize_markdown_structure(content: dict) -> dict:
    previous_heading_level = 0

    for cell in content.get("cells", []):
        if cell.get("cell_type") != "markdown":
            continue

        source_lines = cell.get("source", [])
        if not source_lines:
            continue

        updated_lines = strip_leading_transition(source_lines)
        updated_lines = convert_html_anchor_to_myst_target(updated_lines)

        for idx, line in enumerate(updated_lines):
            heading_match = HEADING_RE.match(line)
            if not heading_match:
                if line.strip():
                    break
                continue

            heading_level = len(heading_match.group(1))
            if previous_heading_level and heading_level > previous_heading_level + 1:
                heading_level = previous_heading_level + 1
                updated_lines[idx] = "#" * heading_level + heading_match.group(2)

            previous_heading_level = heading_level
            break

        cell["source"] = updated_lines

    return content


def strip_leading_transition(source_lines: list[str]) -> list[str]:
    first_content_idx = next((idx for idx, line in enumerate(source_lines) if line.strip()), None)
    if first_content_idx is None:
        return source_lines
    if source_lines[first_content_idx].strip() != "---":
        return source_lines

    next_content_idx = next(
        (idx for idx in range(first_content_idx + 1, len(source_lines)) if source_lines[idx].strip()),
        None,
    )
    if next_content_idx is None or not source_lines[next_content_idx].lstrip().startswith("#"):
        return source_lines

    return source_lines[:first_content_idx] + source_lines[next_content_idx:]


def convert_html_anchor_to_myst_target(source_lines: list[str]) -> list[str]:
    for idx, line in enumerate(source_lines):
        if not line.strip():
            continue

        anchor_match = ANCHOR_RE.match(line)
        if not anchor_match:
            return source_lines

        next_content_idx = next((pos for pos in range(idx + 1, len(source_lines)) if source_lines[pos].strip()), None)
        if next_content_idx is None:
            return source_lines

        if HEADING_RE.match(source_lines[next_content_idx].lstrip()):
            updated_lines = list(source_lines)
            updated_lines[idx] = f"({anchor_match.group(1)})=\n"
            return updated_lines
        return source_lines

    return source_lines


def ensure_cell_ids(content: dict, path: Path) -> dict:
    used_ids = set()

    for idx, cell in enumerate(content.get("cells", [])):
        cell_id = cell.get("id")
        if cell_id:
            used_ids.add(cell_id)
            continue

        source = cell.get("source", [])
        source_text = "".join(source) if isinstance(source, list) else str(source)
        digest = hashlib.sha1(
            f"{path.as_posix()}::{idx}::{cell.get('cell_type', '')}::{source_text}".encode("utf-8")
        ).hexdigest()[:12]
        cell_id = f"c{digest}"

        while cell_id in used_ids:
            digest = hashlib.sha1(f"{cell_id}::{path.as_posix()}".encode("utf-8")).hexdigest()[:12]
            cell_id = f"c{digest}"

        cell["id"] = cell_id
        used_ids.add(cell_id)

    return content


def create_chapter_title(material: dict) -> Path:
    chapter_title = BOOK_TUTORIALS_DIR / material["slug"] / "chapter_title.md"
    part_label = display_part_label(material["part"])
    chapter_title.write_text(
        f"# {part_label}: {material['name']}\n\n"
        f"This session collects the curated material for **{material['name']}**.\n",
        encoding="utf-8",
    )
    return chapter_title


def build_sections(material: dict) -> list[dict]:
    slug = material["slug"]
    staged_dir = BOOK_TUTORIALS_DIR / slug
    sections = []

    intro_name = material.get("intro")
    if intro_name:
        intro_path = staged_dir / ROLE / f"{intro_name}.ipynb"
        if intro_path.exists():
            preprocess_notebook(intro_path)
            sections.append({"file": notebook_file_slug(intro_path.relative_to(BOOK_DIR))})

    for tutorial in material["tutorials"]:
        tutorial_path = staged_dir / ROLE / f"{tutorial}.ipynb"
        if tutorial_path.exists():
            preprocess_notebook(tutorial_path)
            sections.append({"file": notebook_file_slug(tutorial_path.relative_to(BOOK_DIR))})

    outro_name = material.get("outro")
    if outro_name:
        outro_path = staged_dir / ROLE / f"{outro_name}.ipynb"
        if outro_path.exists():
            preprocess_notebook(outro_path)
            sections.append({"file": notebook_file_slug(outro_path.relative_to(BOOK_DIR))})

    if material.get("include_further_reading"):
        sections.append({"file": f"tutorials/{slug}/further_reading"})

    summary_name = material.get("day_summary")
    if summary_name:
        summary_path = staged_dir / ROLE / f"{summary_name}.ipynb"
        if summary_path.exists():
            preprocess_notebook(summary_path)
            sections.append({"file": notebook_file_slug(summary_path.relative_to(BOOK_DIR))})

    return sections


def main() -> None:
    materials = yaml.safe_load(MATERIALS_FILE.read_text(encoding="utf-8"))
    reset_staged_tutorials()
    stage_shared_assets()

    toc = {"format": "jb-book", "root": "home", "parts": []}
    parts_by_caption: dict[str, dict] = {}

    for material in materials:
        stage_material(material)
        chapter_title = create_chapter_title(material)
        chapter = {
            "file": notebook_file_slug(chapter_title.relative_to(BOOK_DIR)),
            "title": material["name"],
            "sections": build_sections(material),
        }

        caption = display_part_label(material["part"])
        if caption not in parts_by_caption:
            part = {"caption": caption, "chapters": []}
            parts_by_caption[caption] = part
            toc["parts"].append(part)
        parts_by_caption[caption]["chapters"].append(chapter)

    toc_path = BOOK_DIR / "_toc.yml"
    toc_path.write_text(yaml.safe_dump(toc, sort_keys=False), encoding="utf-8")


if __name__ == "__main__":
    main()
