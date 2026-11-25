"""Upload safety checks: names, extensions, real content, ZIP/PDF."""

from __future__ import annotations

import io
import zipfile

import pytest

from app.services import upload_guard as g

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
PDF = b"%PDF-1.7\n1 0 obj<<>>endobj\n%%EOF"


def _zip(entries: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in entries.items():
            z.writestr(name, data)
    return buf.getvalue()


@pytest.mark.parametrize(
    "path,data",
    [
        ("a/notes.md", b"# ciao"),
        ("data.csv", b"a,b\n1,2\n"),
        ("x.png", PNG),
        ("x.JPG", b"\xff\xd8\xff\xe0" + b"0" * 8),
        ("x.gif", b"GIF89a" + b"0" * 8),
        ("x.webp", b"RIFF\x00\x00\x00\x00WEBPVP8 "),
        ("doc.pdf", PDF),
        ("old.doc", bytes.fromhex("D0CF11E0A1B11AE1") + b"0" * 8),
        ("w.docx", _zip({"word/document.xml": b"<x/>"})),
        ("p.zip", _zip({"src/main.c": b"int main(){}"})),
    ],
)
def test_valid_uploads_pass(path, data):
    g.validate_upload(path, data)


@pytest.mark.parametrize(
    "path,status",
    [
        ("tool.exe", 415),
        ("page.html", 415),
        ("pic.svg", 415),
        ("noext", 415),
        ("report.exe.pdf", 400),
        ("a.sh.md", 400),
        ("CON.txt", 400),
        ("bad\x07name.md", 400),
        ("evil‮gnp.md", 400),
        ("trailing.", 400),
        ("x" * 130 + ".md", 400),
        ("a:b.md", 400),
    ],
)
def test_bad_names_and_types_rejected(path, status):
    with pytest.raises(g.UploadRejected) as e:
        g.validate_upload(path, b"hello")
    assert e.value.status == status


@pytest.mark.parametrize(
    "path,data",
    [
        ("fake.png", b"not a png"),
        ("fake.pdf", b"MZ\x90\x00"),
        ("fake.docx", b"plain text"),
        ("bin.txt", b"abc\x00def"),
        ("latin1.md", "caffè".encode("latin-1")),
        ("empty.md", b""),
        ("js.pdf", PDF + b"\n<< /S /JavaScript /JS (app.alert(1)) >>"),
        ("macro.docx", _zip({"word/vbaProject.bin": b"x"})),
        ("trav.zip", _zip({"../evil.sh": b"x"})),
        ("bomb.zip", _zip({"a.txt": b"0" * 5_000_000})),
    ],
)
def test_content_mismatch_and_active_content_rejected(path, data):
    with pytest.raises(g.UploadRejected) as e:
        g.validate_upload(path, data)
    assert e.value.status == 422


# --- Endpoint --------------------------------------------------------------------


async def test_contribute_endpoint_rejects_exe_and_fake_pdf(client):
    from tests.test_github import _server_app_settings

    _server_app_settings(client)
    r = await client.post(
        "/github/contribute", json={"section": "material", "path": "a.exe", "content": "hi"}
    )
    assert r.status_code == 415
    r = await client.post(
        "/github/contribute",
        json={"section": "material", "path": "a.pdf", "content": "bm90IGEgcGRm", "encoding": "base64"},
    )
    assert r.status_code == 422
