"""La Bacheca: posts CRUD, likes, comments, and ownership (IDOR) rules."""

from __future__ import annotations


async def _create_post(client, **overrides):
    payload = {"content": "Sessione minishell in cluster alle 15!", "category": "studio"}
    payload.update(overrides)
    resp = await client.post("/posts", json=payload)
    assert resp.status_code == 201, resp.text
    return resp.json()


async def test_create_and_list_post(client):
    created = await _create_post(client, title="Peer learning")
    assert created["title"] == "Peer learning"
    assert created["category"] == "studio"
    assert created["is_mine"] is True
    assert created["like_count"] == 0

    resp = await client.get("/posts")
    assert resp.status_code == 200
    page = resp.json()
    assert page["next_cursor"] is None
    posts = page["items"]
    assert len(posts) == 1
    assert posts[0]["id"] == created["id"]
    assert posts[0]["post_type"] == "post"


async def test_category_filter(client):
    await _create_post(client, category="studio")
    await _create_post(client, category="evento_casuale")
    resp = await client.get("/posts", params={"category": "evento_casuale"})
    assert resp.status_code == 200
    data = resp.json()["items"]
    assert len(data) == 1
    assert data[0]["category"] == "evento_casuale"


async def test_category_filter_multi(client):
    await _create_post(client, category="studio")
    await _create_post(client, category="evento_casuale")
    await _create_post(client, category="mercatino")
    resp = await client.get("/posts", params=[("category", "studio"), ("category", "mercatino")])
    assert resp.status_code == 200
    cats = {p["category"] for p in resp.json()["items"]}
    assert cats == {"studio", "mercatino"}


async def test_invalid_category_rejected(client):
    resp = await client.post("/posts", json={"content": "x", "category": "not_a_category"})
    assert resp.status_code == 422


async def test_empty_content_rejected(client):
    resp = await client.post("/posts", json={"content": "   ", "category": "studio"})
    assert resp.status_code == 422


async def test_like_toggle(client):
    post = await _create_post(client)
    pid = post["id"]

    r1 = await client.post(f"/posts/{pid}/like")
    assert r1.status_code == 200
    assert r1.json() == {"liked": True, "like_count": 1}

    r2 = await client.post(f"/posts/{pid}/like")
    assert r2.json() == {"liked": False, "like_count": 0}


async def test_comment_flow_and_counts(client):
    post = await _create_post(client)
    pid = post["id"]

    rc = await client.post(f"/posts/{pid}/comments", json={"content": "Ce sto! Porto i biscotti."})
    assert rc.status_code == 201
    assert rc.json()["is_mine"] is True

    detail = await client.get(f"/posts/{pid}")
    body = detail.json()
    assert body["comment_count"] == 1
    assert len(body["comments"]) == 1


async def test_owner_can_edit_and_delete(client):
    post = await _create_post(client)
    pid = post["id"]

    upd = await client.patch(f"/posts/{pid}", json={"content": "Aggiornato: alle 16!"})
    assert upd.status_code == 200
    assert upd.json()["content"] == "Aggiornato: alle 16!"

    dele = await client.delete(f"/posts/{pid}")
    assert dele.status_code == 204
    assert (await client.get(f"/posts/{pid}")).status_code == 404


async def test_non_owner_cannot_edit_or_delete(client, users):
    # Alice creates a post...
    post = await _create_post(client)
    pid = post["id"]

    # ...now switch the logged-in user to Bob.
    client.auth_ctx.current = users["bob"]

    upd = await client.patch(f"/posts/{pid}", json={"content": "hijack"})
    assert upd.status_code == 403

    dele = await client.delete(f"/posts/{pid}")
    assert dele.status_code == 403

    # Bob CAN still like it and comment on it (not an ownership action).
    like = await client.post(f"/posts/{pid}/like")
    assert like.status_code == 200
    assert like.json()["liked"] is True


async def test_non_owner_cannot_delete_comment(client, users):
    post = await _create_post(client)
    pid = post["id"]
    rc = await client.post(f"/posts/{pid}/comments", json={"content": "mio commento"})
    comment_id = rc.json()["id"]

    client.auth_ctx.current = users["bob"]
    resp = await client.delete(f"/comments/{comment_id}")
    assert resp.status_code == 403


async def test_missing_post_404(client):
    assert (await client.get("/posts/999999")).status_code == 404


# --- search (?q=) over title, description, author and comments ----------------


async def _ids(client, **params):
    resp = await client.get("/posts", params=params)
    assert resp.status_code == 200, resp.text
    return [p["id"] for p in resp.json()["items"]]


async def test_search_title_description_and_case_insensitive(client):
    a = await _create_post(client, title="Peer Learning", content="boh")
    b = await _create_post(client, title=None, content="Cerco un Compagno per la minishell")
    await _create_post(client, title="altro", content="niente")
    assert await _ids(client, q="peer learning") == [a["id"]]  # title, any case
    assert await _ids(client, q="COMPAGNO") == [b["id"]]  # description


async def test_search_by_author(client, users):
    mine = await _create_post(client, content="post di alice")
    client.auth_ctx.current = users["bob"]
    theirs = await _create_post(client, content="post di bob")
    assert await _ids(client, q="alice") == [mine["id"]]  # login
    assert await _ids(client, q="Bob") == [theirs["id"]]  # display name


async def test_search_in_comments_no_duplicates(client):
    hit = await _create_post(client, content="niente di speciale")
    other = await _create_post(client, content="altro")
    for text in ("la parola magica", "ancora magica qui"):
        r = await client.post(f"/posts/{hit['id']}/comments", json={"content": text})
        assert r.status_code == 201
    assert await _ids(client, q="magica") == [hit["id"]]  # once, despite 2 matching comments
    assert other["id"] not in await _ids(client, q="magica")


async def test_search_composes_with_filters_and_cursor(client):
    s1 = await _create_post(client, content="minishell uno", category="studio")
    await _create_post(client, content="minishell due", category="mercatino")
    s3 = await _create_post(client, content="minishell tre", category="studio")
    assert set(await _ids(client, q="minishell", category="studio")) == {s1["id"], s3["id"]}
    page = (await client.get("/posts", params={"q": "minishell", "limit": 1})).json()
    assert len(page["items"]) == 1 and page["next_cursor"] is not None
    nxt = (
        await client.get("/posts", params={"q": "minishell", "limit": 5, "cursor": page["next_cursor"]})
    ).json()
    assert len(nxt["items"]) == 2  # the remaining matches, none repeated
    assert not {p["id"] for p in nxt["items"]} & {p["id"] for p in page["items"]}


async def test_search_short_query_ignored_and_wildcards_literal(client):
    await _create_post(client, content="uno")
    await _create_post(client, content="due")
    assert len(await _ids(client, q="u")) == 2  # 1 char → no filter
    assert await _ids(client, q="%%") == []  # wildcards are literal
    assert await _ids(client, q="_n") == []
    assert (await client.get("/posts", params={"q": "x" * 65})).status_code == 422
