"""File-based Materiale/Archivio content: listing, reading, and safety."""

from __future__ import annotations

import pytest

from app.config import get_settings
from app.services import content as content_service
from app.services.exceptions import NotFoundError


def test_list_material_finds_sample_file():
    entries = content_service.list_entries(get_settings(), "material").entries
    assert "exam02/help.md" in [e.path for e in entries]


def test_read_material_file_returns_content():
    f = content_service.read_file(get_settings(), "material", "exam02/help.md")
    assert "Exam Rank 02" in f.content


def test_unknown_section_rejected():
    with pytest.raises(NotFoundError):
        content_service.list_entries(get_settings(), "secrets")


@pytest.mark.parametrize("bad", ["../../etc/passwd", "/etc/passwd", "../config.py", "exam02/../../x"])
def test_path_traversal_rejected(bad):
    with pytest.raises(NotFoundError):
        content_service.read_file(get_settings(), "material", bad)


def test_resolve_file_returns_mime_and_blocks_traversal():
    path, mime = content_service.resolve_file(get_settings(), "material", "libft/diagram.svg")
    assert mime == "image/svg+xml" and path.name == "diagram.svg"
    with pytest.raises(NotFoundError):
        content_service.resolve_file(get_settings(), "material", "../../../etc/passwd")


def test_entry_kind_classification():
    by_path = {e.path: e for e in content_service.list_entries(get_settings(), "material").entries}
    assert by_path["exam02/help.md"].kind == "text"
    assert by_path["libft/diagram.svg"].kind == "image"
