"""Tests for document preview service."""

from services.generation.preview_service import build_document_preview


def test_preview_markdown(tmp_path):
    path = tmp_path / "readme.md"
    path.write_text("# Title\n\nHello world", encoding="utf-8")
    result = build_document_preview(str(path), "md")
    assert result["preview_type"] == "markdown"
    assert "Title" in result["content"]


def test_preview_code(tmp_path):
    path = tmp_path / "app.py"
    path.write_text("def main():\n    print('hi')\n", encoding="utf-8")
    result = build_document_preview(str(path), "py")
    assert result["preview_type"] == "code"
    assert result["language"] == "py"
    assert "def main" in result["content"]


def test_preview_csv(tmp_path):
    path = tmp_path / "data.csv"
    path.write_text("name,value\nfoo,1\nbar,2\n", encoding="utf-8")
    result = build_document_preview(str(path), "csv")
    assert result["preview_type"] == "csv"
    assert result["table"]["headers"] == ["name", "value"]
