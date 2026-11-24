"""File-based Materiale/Archivio content: listing, reading, and safety.

Self-contained: builds its own temp ``assets`` tree so it doesn't depend on
whatever real content lives in the repo.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
import respx
from httpx import Response as HttpxResponse

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


# --- GitHub source ---------------------------------------------------------

_TREE = {
    "tree": [
        {"path": "assets/material/exam02/help.md", "type": "blob", "size": 20},
        {"path": "assets/material/.hidden", "type": "blob", "size": 1},
        {"path": "assets/archive/recap.md", "type": "blob", "size": 5},
        {"path": "README.md", "type": "blob", "size": 9},  # app code, excluded
    ]
}


def _with_github(assets):
    return SimpleNamespace(
        **vars(assets),
        github_repo="TioElvis/42-studenti",
        github_branch="main",
        github_token="",
        github_cache_ttl=300,
    )


async def test_github_listing_and_text(assets):
    content_service.invalidate_github_cache()
    s = _with_github(assets)
    with respx.mock(assert_all_called=False) as mock:
        mock.get(
            url__startswith="https://api.github.com/repos/TioElvis/42-studenti/git/trees/main"
        ).mock(return_value=HttpxResponse(200, json=_TREE))
        mock.get(
            "https://raw.githubusercontent.com/TioElvis/42-studenti/main/assets/material/exam02/help.md"
        ).mock(return_value=HttpxResponse(200, text="# Help da GitHub"))

        listing = await content_service.get_listing(s, "material")
        # Only material blobs; hidden file, archive and app code excluded.
        assert {e.path for e in listing.entries} == {"exam02/help.md"}
        text = await content_service.get_text(s, "material", "exam02/help.md")
        assert "GitHub" in text.content
    content_service.invalidate_github_cache()


async def test_github_unavailable_falls_back_to_local(assets):
    content_service.invalidate_github_cache()
    s = _with_github(assets)  # assets_dir points at the local temp tree
    with respx.mock(assert_all_called=False) as mock:
        mock.get(url__startswith="https://api.github.com/repos/").mock(
            return_value=HttpxResponse(500)
        )
        listing = await content_service.get_listing(s, "material")
        assert "exam02/help.md" in {e.path for e in listing.entries}  # local fallback
    content_service.invalidate_github_cache()


async def test_github_traversal_rejected(assets):
    s = _with_github(assets)
    with pytest.raises(NotFoundError):
        await content_service.get_text(s, "material", "../../../etc/passwd")
