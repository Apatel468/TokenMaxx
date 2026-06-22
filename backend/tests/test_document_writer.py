"""Tests for document file writing."""

from pathlib import Path

from services.generation.document_writer import write_document_file


def test_write_markdown_file(tmp_path):
    path = tmp_path / "readme.md"
    final, mime, count = write_document_file(
        path, "# Hello\n\nWorld", "md", title="readme"
    )
    assert final.exists()
    assert final.read_text(encoding="utf-8").startswith("# Hello")
    assert mime == "text/markdown"
    assert count == 1


def test_write_json_file(tmp_path):
    path = tmp_path / "config.json"
    final, mime, count = write_document_file(
        path, '{"name": "test"}', "json"
    )
    assert final.exists()
    assert '"name"' in final.read_text(encoding="utf-8")
    assert count == 1


def test_write_project_zip(tmp_path):
    path = tmp_path / "project.zip"
    content = (
        "=== README.md ===\n# Project\n\n"
        "=== app/main.py ===\nprint('hi')\n"
    )
    final, mime, count = write_document_file(
        path, content, "zip", is_project=True
    )
    assert final.suffix == ".zip"
    assert final.exists()
    assert count == 2
    assert mime == "application/zip"
