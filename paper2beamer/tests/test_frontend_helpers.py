"""Tests for the frontend's deterministic helpers using a FAKE Docling document.

Docling itself is heavy (downloads models) and needs a real PDF, so these tests
exercise the pure extraction/linking logic against hand-built stand-ins. The
``import frontend_docling`` is safe without Docling because the Docling import is
lazy (inside ``_import_docling``), not at module load.
"""

from __future__ import annotations

import os
from types import SimpleNamespace

import frontend_docling as fd


class _Label:
    """Mimics a DocItemLabel enum member with a ``.value`` string."""

    def __init__(self, value: str) -> None:
        self.value = value


def _text_item(label: str, text: str):
    return SimpleNamespace(label=_Label(label), text=text)


class _FakeDoc:
    """Minimal stand-in exposing the surface frontend_docling reads."""

    def __init__(self, items, pictures=None, tables=None, name="paper"):
        self._items = items
        self.pictures = pictures or []
        self.tables = tables or []
        self.name = name

    def iterate_items(self):
        for it in self._items:
            yield it, 0


def test_extract_sections_groups_by_headers():
    doc = _FakeDoc([
        _text_item("text", "abstract line before any header"),
        _text_item("section_header", "Introduction"),
        _text_item("text", "intro body"),
        _text_item("caption", "Figure 1: ignore me"),   # captions skipped
        _text_item("section_header", "Method"),
        _text_item("text", "method body one"),
        _text_item("text", "method body two"),
    ])
    title, sections = fd._extract_sections(doc)
    assert title == ""   # no title-labelled item present
    titles = [s["title"] for s in sections]
    assert titles == ["Frontmatter", "Introduction", "Method"]
    method = sections[2]
    assert method["text"] == "method body one\nmethod body two"
    # Caption text must not leak into a section body.
    assert "ignore me" not in method["text"]
    # Section ids are unique.
    assert len({s["id"] for s in sections}) == len(sections)


def test_extract_sections_captures_title_separately():
    doc = _FakeDoc([
        _text_item("title", "My Great Paper"),
        _text_item("section_header", "Introduction"),
        _text_item("text", "intro body"),
    ])
    title, sections = fd._extract_sections(doc)
    assert title == "My Great Paper"
    # The title must NOT also appear as a section.
    assert [s["title"] for s in sections] == ["Introduction"]


def test_extract_sections_no_headers_keeps_frontmatter():
    doc = _FakeDoc([_text_item("text", "just some floating text")])
    title, sections = fd._extract_sections(doc)
    assert title == ""
    assert len(sections) == 1
    assert sections[0]["text"] == "just some floating text"


def test_link_references_matches_figure_numbers():
    sections = [
        {"id": "sec1", "title": "Intro", "text": "We refer to Figure 3 here."},
        {"id": "sec2", "title": "Other", "text": "No figures mentioned."},
    ]
    figures = [
        {"id": "fig1", "caption": "Figure 3: the thing", "referenced_in": []},
        {"id": "fig2", "caption": "Figure 7: elsewhere", "referenced_in": []},
    ]
    fd._link_references(sections, figures)
    assert figures[0]["referenced_in"] == ["sec1"]   # fig "3" mentioned in sec1
    assert figures[1]["referenced_in"] == []          # fig "7" mentioned nowhere


def test_label_of_is_version_tolerant():
    assert fd._label_of(_text_item("section_header", "x")) == "section_header"
    assert fd._label_of(SimpleNamespace(label="text")) == "text"   # plain string label
    assert fd._label_of(SimpleNamespace()) == ""                    # no label attr


def test_page_of_reads_provenance():
    item = SimpleNamespace(prov=[SimpleNamespace(page_no=4)])
    assert fd._page_of(item) == 4
    assert fd._page_of(SimpleNamespace(prov=[])) is None
    assert fd._page_of(SimpleNamespace()) is None


def test_extract_figures_handles_unrenderable_picture(tmp_path):
    """A picture whose get_image returns None is skipped, not fatal."""
    class _Pic:
        def get_image(self, _doc):
            return None

        def caption_text(self, _doc):
            return "cap"

    doc = _FakeDoc(items=[], pictures=[_Pic()])
    figures_dir = os.path.join(tmp_path, "figures")
    registry = fd._extract_figures(doc, figures_dir, str(tmp_path))
    assert registry == []   # nothing registered, no crash
