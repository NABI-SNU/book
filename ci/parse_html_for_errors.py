import sys
from pathlib import Path

import yaml
from bs4 import BeautifulSoup


ROLE = sys.argv[1]
HTML_DIR = Path("book/_build/html")
MATERIALS_FILE = Path("tutorials/materials.yml")


def html_path(slug: str, notebook_name: str) -> Path:
    return HTML_DIR / "tutorials" / slug / ROLE / f"{notebook_name}.html"


def clean_html(path: Path) -> None:
    contents = path.read_text(encoding="utf-8")
    parsed = BeautifulSoup(contents, features="html.parser")

    for div in parsed.find_all("div", {"class": "cell_output docutils container"}):
        if "NotImplementedError" in str(div) or "NameError" in str(div):
            div.decompose()

    for img in parsed.find_all("img", alt=True):
        if img["alt"] == "Solution hint":
            img["align"] = "center"
            img["class"] = "align-center"

    path.write_text(str(parsed), encoding="utf-8")


def main() -> None:
    materials = yaml.safe_load(MATERIALS_FILE.read_text(encoding="utf-8"))
    for material in materials:
        for tutorial in material["tutorials"]:
            path = html_path(material["slug"], tutorial)
            if path.exists():
                clean_html(path)


if __name__ == "__main__":
    main()
