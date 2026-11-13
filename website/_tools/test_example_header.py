import json
import shutil
import subprocess
from pathlib import Path

import pytest
from bs4 import BeautifulSoup, Tag

HERE = Path(__file__).parent
FILTER_DIR = HERE.parent / "_filters" / "example-header"
FIXTURE = HERE / "fixtures" / "example_header"


@pytest.fixture(scope="module")
def soup(tmp_path_factory: pytest.TempPathFactory) -> BeautifulSoup:
    if shutil.which("quarto") is None:
        pytest.skip("quarto not installed")
    work = tmp_path_factory.mktemp("example_header")
    shutil.copytree(FIXTURE, work, dirs_exist_ok=True)
    for f in FILTER_DIR.iterdir():
        shutil.copy(f, work)
    subprocess.run(
        ["quarto", "render", "index.md", "--to", "html"],
        cwd=work,
        check=True,
        capture_output=True,
    )
    return BeautifulSoup((work / "index.html").read_text(), "html.parser")


SHOWCASE_FIXTURE = HERE / "fixtures" / "example_showcase"


@pytest.fixture(scope="module")
def showcase_soup(tmp_path_factory: pytest.TempPathFactory) -> BeautifulSoup:
    if shutil.which("quarto") is None:
        pytest.skip("quarto not installed")
    work = tmp_path_factory.mktemp("example_showcase")
    shutil.copytree(SHOWCASE_FIXTURE, work, dirs_exist_ok=True)
    for f in FILTER_DIR.iterdir():
        shutil.copy(f, work)
    subprocess.run(
        ["quarto", "render", "index.md", "--to", "html"],
        cwd=work,
        check=True,
        capture_output=True,
    )
    return BeautifulSoup((work / "index.html").read_text(), "html.parser")


def test_explicit_shinylive_link(showcase_soup: BeautifulSoup) -> None:
    links = showcase_soup.select("a.sw-shinylive-link")
    assert [(a["href"], a["data-example"]) for a in links] == [("app.py", "app.py")]
    assert links[0].text == "Open in Shinylive"


def test_plain_app_link_untouched(showcase_soup: BeautifulSoup) -> None:
    plain = [a for a in showcase_soup.select('a[href="app.py"]') if "sw-shinylive-link" not in a.get_attribute_list("class")]
    assert len(plain) == 1
    assert plain[0].text == "app.py"
    assert not plain[0].has_attr("data-example")


def test_showcase_bundle_uses_page_requirements(showcase_soup: BeautifulSoup) -> None:
    script = showcase_soup.select_one("#sw-example-bundles")
    assert script
    bundles = json.loads(script.text)
    assert set(bundles) == {"app.py"}
    assert bundles["app.py"] == [
        {"name": "app.py", "content": (SHOWCASE_FIXTURE / "app.py").read_text()},
        {"name": "requirements.txt", "content": (SHOWCASE_FIXTURE / "requirements.txt").read_text()},
    ]


def examples(soup: BeautifulSoup) -> list[Tag]:
    return soup.select(".sw-example")


def lines_of(name: str) -> int:
    return len((FIXTURE / "examples" / name).read_text().strip("\n").splitlines())


def test_every_tagged_block_gets_a_bar(soup: BeautifulSoup) -> None:
    exs = examples(soup)
    assert len(exs) == 3
    for ex in exs:
        assert ex.select_one(".sw-example-bar")
        assert ex.select_one(".sw-example-code div.sourceCode")
    untagged = [
        d for d in soup.select("div.sourceCode") if d.find_parent(class_="sw-example") is None
    ]
    assert len(untagged) == 2


def test_bar_contents(soup: BeautifulSoup) -> None:
    bar = examples(soup)[0]
    file = bar.select_one(".sw-example-file")
    assert file and file["href"] == "examples/a.py" and file.text == "examples/a.py"
    extras = bar.select(".sw-example-extra")
    assert [(e["href"], e.text) for e in extras] == [("examples/helper.py", "+ helper.py")]
    actions = [a["data-action"] for a in bar.select(".sw-example-action")]
    assert actions == ["open", "copy", "shinylive"]
    meta = bar.select_one(".sw-example-meta")
    assert meta and meta.text == f"{lines_of('a.py')} lines"


def test_excerpt_meta(soup: BeautifulSoup) -> None:
    meta = examples(soup)[1].select_one(".sw-example-meta")
    assert meta and meta.text == f"excerpt · 2 of {lines_of('b.py')} lines"


def test_collapse(soup: BeautifulSoup) -> None:
    exs = examples(soup)
    collapsed = ["sw-collapsed" in ex.get_attribute_list("class") for ex in exs]
    assert collapsed == [False, True, False]
    ids: list[str] = []
    for ex, is_collapsed in zip(exs, collapsed):
        toggle = ex.select_one(".sw-example-toggle")
        code = ex.select_one(".sw-example-code")
        assert toggle and code
        assert toggle["aria-expanded"] == ("false" if is_collapsed else "true")
        assert toggle["aria-controls"] == code["id"]
        ids.append(str(code["id"]))
    assert len(set(ids)) == 3


def test_indented_block_in_list(soup: BeautifulSoup) -> None:
    assert sum(ex.find_parent("li") is not None for ex in examples(soup)) == 1


def test_prose_links(soup: BeautifulSoup) -> None:
    links = soup.select("a.sw-shinylive-link")
    assert [(a["href"], a["data-example"]) for a in links] == [
        ("examples/a.py", "examples/a.py"),
        ("examples/tpl.py", "examples/tpl.py"),
    ]
    assert soup.select(".sw-example-bar .sw-shinylive-link") == []


def test_bundles(soup: BeautifulSoup) -> None:
    script = soup.select_one("#sw-example-bundles")
    assert script
    bundles = json.loads(script.text)
    assert set(bundles) == {"examples/a.py", "examples/b.py", "examples/tpl.py"}
    ex = FIXTURE / "examples"
    assert bundles["examples/a.py"] == [
        {"name": "app.py", "content": (ex / "a.py").read_text()},
        {"name": "helper.py", "content": (ex / "helper.py").read_text()},
        {"name": "requirements.txt", "content": "shinywidgets[plotly]\n"},
    ]
    assert bundles["examples/b.py"][0]["content"] == (ex / "b.py").read_text()


def test_dependency_scripts(soup: BeautifulSoup) -> None:
    srcs = [str(s.get("src", "")) for s in soup.select("script")]
    assert any(s.endswith("lz-string.min.js") for s in srcs)
    assert any(s.endswith("example-header.js") for s in srcs)
