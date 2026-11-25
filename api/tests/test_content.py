"""Materiale/Archivio content: GitHub metadata-only listing, proxy, path safety.

Everything is mocked (respx); no file from assets/ is ever read from disk.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
import respx
from httpx import Response as HttpxResponse

from app.services import content as content_service
from app.services.exceptions import ContentUnavailableError, NotFoundError

_TREE = {
    "tree": [
        {"path": "assets/material/exam02/help.md", "type": "blob", "size": 20, "sha": "aaa"},
        {"path": "assets/material/exam02/ex03/notes.md", "type": "blob", "size": 7, "sha": "bbb"},
        {"path": "assets/material/empty/sub/.gitkeep", "type": "blob", "size": 0, "sha": "ccc"},
        {"path": "assets/material/.hidden", "type": "blob", "size": 1, "sha": "ddd"},
        {"path": "assets/material/exam02", "type": "tree"},
        {"path": "assets/archive/recap.md", "type": "blob", "size": 5, "sha": "eee"},
        {"path": "README.md", "type": "blob", "size": 9, "sha": "fff"},  # app code
    ]
}

_TREES_URL = "https://api.github.com/repos/TioElvis/42-studenti/git/trees/main"


def _settings(repo: str = "TioElvis/42-studenti"):
    return SimpleNamespace(
        github_repo=repo,
        github_branch="main",
        github_write_token="",
        github_cache_ttl=300,
        http_cache_seconds=60,
    )


@pytest.fixture(autouse=True)
def _clear_cache():
    content_service.invalidate_github_cache()
    yield
    content_service.invalidate_github_cache()


async def test_listing_is_metadata_only_with_github_urls():
    with respx.mock(assert_all_called=False) as mock:
        trees = mock.get(url__startswith=_TREES_URL).mock(
            return_value=HttpxResponse(200, json=_TREE)
        )
        contents = mock.get(url__regex=r".*/contents/.*").mock(return_value=HttpxResponse(500))
        raw = mock.get(url__startswith="https://raw.githubusercontent.com/").mock(
            return_value=HttpxResponse(500)
        )
        listing = await content_service.get_listing(_settings(), "material")
        # Only the Trees endpoint was hit: no file content was downloaded.
        assert trees.called and not contents.called and not raw.called

    by_path = {e.path: e for e in listing.entries}
    # Only material blobs; .gitkeep, hidden files, archive and app code excluded.
    assert set(by_path) == {"exam02/help.md", "exam02/ex03/notes.md"}
    e = by_path["exam02/ex03/notes.md"]
    assert e.folder == "exam02/ex03" and e.sha == "bbb" and e.kind == "text"
    assert e.github_url == (
        "https://github.com/TioElvis/42-studenti/blob/main/assets/material/exam02/ex03/notes.md"
    )
    assert e.raw_url == (
        "https://raw.githubusercontent.com/TioElvis/42-studenti/main/assets/material/exam02/ex03/notes.md"
    )


async def test_nested_and_empty_folders_listed():
    with respx.mock(assert_all_called=False) as mock:
        mock.get(url__startswith=_TREES_URL).mock(return_value=HttpxResponse(200, json=_TREE))
        listing = await content_service.get_listing(_settings(), "material")
    # empty/sub holds only .gitkeep: still a folder, but adds no file entries.
    assert listing.folders == ["empty", "empty/sub", "exam02", "exam02/ex03"]
    assert not any(e.folder.startswith("empty") for e in listing.entries)


async def test_text_is_proxied_from_raw_in_memory():
    s = _settings()
    with respx.mock(assert_all_called=False) as mock:
        mock.get(
            "https://raw.githubusercontent.com/TioElvis/42-studenti/main/assets/material/exam02/help.md"
        ).mock(return_value=HttpxResponse(200, text="# Help da GitHub"))
        text = await content_service.get_text(s, "material", "exam02/help.md")
        assert "GitHub" in text.content
        f = await content_service.get_file(s, "material", "exam02/help.md")
        assert f.data == b"# Help da GitHub" and f.media_type == "text/markdown"


async def test_unknown_section_rejected():
    with pytest.raises(NotFoundError):
        await content_service.get_listing(_settings(), "secrets")


async def test_github_unavailable_is_502_not_local_fallback():
    with respx.mock(assert_all_called=False) as mock:
        mock.get(url__startswith="https://api.github.com/repos/").mock(
            return_value=HttpxResponse(500)
        )
        with pytest.raises(ContentUnavailableError):
            await content_service.get_listing(_settings(), "material")


async def test_unconfigured_repo_unavailable():
    with pytest.raises(ContentUnavailableError):
        await content_service.get_listing(_settings(repo=""), "material")


@pytest.mark.parametrize(
    "bad",
    [
        "../../etc/passwd", "/etc/passwd", "../x", "exam02/../../x", "a\\b.md",
        "exam02/", "/exam02/x.md", "exam02//x.md", "exam02/./x.md", ".hidden", "a/.git/x",
    ],
)
async def test_path_traversal_rejected(bad):
    with pytest.raises(NotFoundError):
        await content_service.get_text(_settings(), "material", bad)
    with pytest.raises(NotFoundError):
        content_service.confine_rel(bad)


@pytest.mark.parametrize("ok", ["exam02/ex03/notes.md", "a.md", "x/y/z/w.pdf"])
def test_nested_paths_allowed(ok):
    assert content_service.confine_rel(ok) == ok


def test_folder_confinement_and_keep_path():
    assert content_service.confine_folder("exam02/ex03") == "exam02/ex03"
    assert content_service.keep_path("exam02/ex03") == "exam02/ex03/.gitkeep"
    for bad in ["", "..", "a/../b", "/a", "a/", "a\\b", "a//b"]:
        with pytest.raises(NotFoundError):
            content_service.confine_folder(bad)
