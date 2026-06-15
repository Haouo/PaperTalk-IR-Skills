from pathlib import Path

import pytest

from scripts.frontend_docling import figure_filename, ingest, relativize_image_refs


def test_figure_filename_zero_pads_and_uses_index():
    assert figure_filename(1, "png") == "figure-001.png"
    assert figure_filename(42, "png") == "figure-042.png"


def test_relativize_image_refs_strips_out_dir_prefix():
    md = "![Image](/tmp/run/figures/image_000.png)\ntext\n"
    out = relativize_image_refs(md, Path("/tmp/run"))
    assert out == "![Image](figures/image_000.png)\ntext\n"


def test_relativize_image_refs_leaves_already_relative_refs():
    md = "![Image](figures/image_000.png)\n"
    assert relativize_image_refs(md, Path("/tmp/run")) == md


def test_figure_filename_rejects_non_positive_index():
    with pytest.raises(ValueError):
        figure_filename(0, "png")


def test_ingest_rejects_missing_pdf(tmp_path):
    with pytest.raises(FileNotFoundError):
        ingest(tmp_path / "nope.pdf", tmp_path / "out")


def test_ingest_rejects_non_pdf_suffix(tmp_path):
    f = tmp_path / "paper.txt"
    f.write_text("not a pdf")
    with pytest.raises(ValueError):
        ingest(f, tmp_path / "out")


@pytest.mark.heavy
def test_ingest_real_pdf_produces_markdown_and_figures(tmp_path):
    # Manual/local only: requires a real sample.pdf and Docling models.
    out = tmp_path / "out"
    md = ingest(Path("tests/fixtures/sample.pdf"), out)
    assert (out / "paper-content.md").is_file()
    assert (out / "figures").is_dir()
    # Figures must actually be persisted, and refs must be relative (portable).
    assert any((out / "figures").iterdir()), "no figures written"
    assert str(out) not in md.read_text(), "image refs leaked an absolute path"
