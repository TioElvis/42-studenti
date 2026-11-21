"""File-based Materiale/Archivio content: listing, reading, and safety.

Self-contained: builds its own temp ``assets`` tree so it doesn't depend on
whatever real content lives in the repo.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.services import content as content_service
from app.services.exceptions import NotFoundError


@pytest.fixture
def assets(tmp_path):
    mat = tmp_path / "material"
    (mat / "exam02").mkdir(parents=True)
    (mat / "exam02" / "help.md").write_text("# Help\nciao regà", encoding="utf-8")
    (mat / "libft").mkdir(parents=True)
    (mat / "libft" / "diagram.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg'/>")
    (tmp_path / "archive").mkdir()
    return SimpleNamespace(assets_dir=str(tmp_path), http_cache_seconds=60)


def test_list_finds_files_with_folders(assets):
    entries = content_service.list_entries(assets, "material").entries
    paths = {e.path for e in entries}
    assert {"exam02/help.md", "libft/diagram.svg"} <= paths


def test_read_text_file(assets):
    assert "Help" in content_service.read_file(assets, "material", "exam02/help.md").content


def test_unknown_section_rejected(assets):
    with pytest.raises(NotFoundError):
        content_service.list_entries(assets, "secrets")


@pytest.mark.parametrize("bad", ["../../etc/passwd", "/etc/passwd", "../x", "exam02/../../x"])
def test_path_traversal_rejected(assets, bad):
    with pytest.raises(NotFoundError):
        content_service.read_file(assets, "material", bad)
    with pytest.raises(NotFoundError):
        content_service.resolve_file(assets, "material", bad)


def test_resolve_file_mime(assets):
    path, mime = content_service.resolve_file(assets, "material", "libft/diagram.svg")
    assert mime == "image/svg+xml" and path.name == "diagram.svg"


def test_entry_kind_classification(assets):
    by_path = {e.path: e for e in content_service.list_entries(assets, "material").entries}
    assert by_path["exam02/help.md"].kind == "text"
    assert by_path["libft/diagram.svg"].kind == "image"
