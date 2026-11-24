"""Post service: feed, detail, ownership-guarded CRUD, likes and comments."""

from __future__ import annotations

from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.comment import Comment
from ..models.enums import PostCategory, PostType
from ..models.like import PostLike
from ..models.post import Post
from ..models.rsvp import PostRSVP
from ..models.user import User
from ..schemas.comment import CommentCreate, CommentOut
from ..schemas.post import (
    CERCO_TEAM_MAX,
    PARTICIPANTS_MAX,
    LikeState,
    PostCreate,
    PostDetail,
    PostOut,
    PostPage,
    PostUpdate,
    RsvpState,
)
from ..schemas.user import UserPublic
from .exceptions import ConflictError, ForbiddenError, NotFoundError

MAX_PAGE_SIZE = 100


def _counts(viewer_id: int):
    like_count = (
        select(func.count(PostLike.id))
        .where(PostLike.post_id == Post.id)
        .correlate(Post)
        .scalar_subquery()
    )
    comment_count = (
        select(func.count(Comment.id))
        .where(Comment.post_id == Post.id)
        .correlate(Post)
        .scalar_subquery()
    )
    liked_by_me = (
        select(func.count(PostLike.id))
        .where(PostLike.post_id == Post.id, PostLike.user_id == viewer_id)
        .correlate(Post)
        .scalar_subquery()
    )
    rsvp_count = (
        select(func.count(PostRSVP.id))
        .where(PostRSVP.post_id == Post.id)
        .correlate(Post)
        .scalar_subquery()
    )
    joined_by_me = (
        select(func.count(PostRSVP.id))
        .where(PostRSVP.post_id == Post.id, PostRSVP.user_id == viewer_id)
        .correlate(Post)
        .scalar_subquery()
    )
    return like_count, comment_count, liked_by_me, rsvp_count, joined_by_me


def _base_query(viewer_id: int) -> Select:
    like_count, comment_count, liked_by_me, rsvp_count, joined_by_me = _counts(viewer_id)
    return select(
        Post,
        like_count.label("like_count"),
        comment_count.label("comment_count"),
        liked_by_me.label("liked_by_me"),
        rsvp_count.label("rsvp_count"),
        joined_by_me.label("joined_by_me"),
    ).options(selectinload(Post.author))


def _to_out(row, viewer_id: int) -> PostOut:
    post: Post = row[0]
    out = PostOut.model_validate(post)
    out.like_count = int(row[1] or 0)
    out.comment_count = int(row[2] or 0)
    out.liked_by_me = bool(row[3])
    out.is_mine = post.author_id == viewer_id
    out.rsvp_count = int(row[4] or 0)
    out.joined_by_me = bool(row[5])
    out.rsvp_full = (
        post.max_participants is not None and out.rsvp_count >= post.max_participants
    )
    return out


async def list_posts(
    session: AsyncSession,
    *,
    viewer_id: int,
    categories: list[PostCategory] | None = None,
    post_type: PostType | None = None,
    cursor: int | None = None,
    limit: int = 20,
) -> PostPage:
    """Cursor-paginated feed, newest first. ``cursor`` is the last seen post id.

    Posts persist indefinitely (no time-based expiry); only the author can
    delete them. ``categories`` (any-of) and ``post_type`` narrow the feed —
    the Bacheca filter bar offers a multi-select of categories plus a Sondaggi
    toggle (``post_type=sondaggio``).
    """
    limit = max(1, min(limit, MAX_PAGE_SIZE))
    stmt = _base_query(viewer_id).order_by(Post.id.desc()).limit(limit + 1)
    if categories:
        stmt = stmt.where(Post.category.in_(categories))
    if post_type is not None:
        stmt = stmt.where(Post.post_type == post_type)
    if cursor is not None:
        stmt = stmt.where(Post.id < cursor)
    rows = (await session.execute(stmt)).all()

    has_more = len(rows) > limit
    rows = rows[:limit]
    items = [_to_out(row, viewer_id) for row in rows]
    next_cursor = items[-1].id if (has_more and items) else None
    return PostPage(items=items, next_cursor=next_cursor)


async def get_detail(session: AsyncSession, *, post_id: int, viewer_id: int) -> PostDetail:
    stmt = _base_query(viewer_id).where(Post.id == post_id).options(
        selectinload(Post.comments).selectinload(Comment.author)
    )
    row = (await session.execute(stmt)).first()
    if row is None:
        raise NotFoundError("Post not found")
    post: Post = row[0]
    detail = PostDetail.model_validate(_to_out(row, viewer_id).model_dump())
    # Resolve each reply's @ref from the comments already loaded for this post.
    login_by_id = {c.id: c.author.login for c in post.comments}
    detail.comments = [
        _comment_out(c, viewer_id, reply_to=login_by_id.get(c.parent_id) if c.parent_id else None)
        for c in sorted(post.comments, key=lambda c: c.created_at)
    ]
    return detail


async def create_post(session: AsyncSession, *, author: User, data: PostCreate) -> PostOut:
    post = Post(
        author_id=author.id,
        title=data.title,
        content=data.content,
        category=data.category,
        post_type=data.post_type,
        max_participants=data.max_participants,
    )
    session.add(post)
    await session.commit()
    return await get_detail(session, post_id=post.id, viewer_id=author.id)


async def _owned_post(session: AsyncSession, post_id: int, user_id: int) -> Post:
    post = await session.get(Post, post_id)
    if post is None:
        raise NotFoundError("Post not found")
    if post.author_id != user_id:
        raise ForbiddenError("You can only modify your own posts")
    return post


async def update_post(
    session: AsyncSession, *, post_id: int, user_id: int, data: PostUpdate
) -> PostOut:
    post = await _owned_post(session, post_id, user_id)
    fields = data.model_dump(exclude_unset=True)
    if "title" in fields:
        post.title = fields["title"]
    if "content" in fields and fields["content"] is not None:
        post.content = fields["content"]
    if "category" in fields and fields["category"] is not None:
        post.category = fields["category"]

    # Capacity edits (sondaggi only). post_type is intentionally immutable.
    provided_max = "max_participants" in fields
    if post.post_type is PostType.SONDAGGIO:
        # Resulting capacity after this edit (new value, or the current one).
        new_max = fields["max_participants"] if provided_max else post.max_participants
        await _validate_sondaggio_capacity(session, post, new_max)
        if provided_max:
            post.max_participants = new_max
    elif provided_max and fields["max_participants"] is not None:
        raise ConflictError("Solo i sondaggi hanno una capacità.")

    await session.commit()
    return await get_detail(session, post_id=post.id, viewer_id=user_id)


async def _validate_sondaggio_capacity(
    session: AsyncSession, post: Post, new_max: int | None
) -> None:
    """Enforce category + 'never below current attendees' rules for a sondaggio."""
    if post.category is PostCategory.CERCO_TEAM:
        if new_max is None or not (1 <= new_max <= CERCO_TEAM_MAX):
            raise ConflictError(
                f"Un sondaggio 'Cerco team' vuole da 1 a {CERCO_TEAM_MAX} partecipanti."
            )
    elif new_max is not None and not (1 <= new_max <= PARTICIPANTS_MAX):
        raise ConflictError("Numero di posti non valido.")

    if new_max is not None:
        current = await _rsvp_count(session, post.id)
        if new_max < current:
            raise ConflictError(
                f"Ci stanno già {current} iscritti: nun poi mette un tetto più basso."
            )


async def delete_post(session: AsyncSession, *, post_id: int, user_id: int) -> None:
    post = await _owned_post(session, post_id, user_id)
    await session.delete(post)
    await session.commit()


async def toggle_like(session: AsyncSession, *, post_id: int, user_id: int) -> LikeState:
    post = await session.get(Post, post_id)
    if post is None:
        raise NotFoundError("Post not found")

    existing = (
        await session.execute(
            select(PostLike).where(PostLike.post_id == post_id, PostLike.user_id == user_id)
        )
    ).scalar_one_or_none()

    if existing is not None:
        await session.delete(existing)
        await session.commit()
        liked = False
    else:
        session.add(PostLike(post_id=post_id, user_id=user_id))
        try:
            await session.commit()
            liked = True
        except IntegrityError:
            # Raced with a concurrent like from the same user; treat as already liked.
            await session.rollback()
            liked = True

    count = await session.scalar(
        select(func.count(PostLike.id)).where(PostLike.post_id == post_id)
    )
    return LikeState(liked=liked, like_count=int(count or 0))


async def _rsvp_count(session: AsyncSession, post_id: int) -> int:
    count = await session.scalar(
        select(func.count(PostRSVP.id)).where(PostRSVP.post_id == post_id)
    )
    return int(count or 0)


async def toggle_rsvp(session: AsyncSession, *, post_id: int, user_id: int) -> RsvpState:
    """Join/leave a sondaggio ("Ci sto!"), enforcing capacity on the server."""
    post = await session.get(Post, post_id)
    if post is None:
        raise NotFoundError("Post not found")
    if post.post_type is not PostType.SONDAGGIO:
        raise ConflictError("Questo post non è un sondaggio")

    existing = (
        await session.execute(
            select(PostRSVP).where(PostRSVP.post_id == post_id, PostRSVP.user_id == user_id)
        )
    ).scalar_one_or_none()

    if existing is not None:
        await session.delete(existing)
        await session.commit()
        joined = False
    else:
        # Strict capacity check: reject if the sondaggio is already full.
        if post.max_participants is not None:
            current = await _rsvp_count(session, post_id)
            if current >= post.max_participants:
                raise ConflictError("Sondaggio al completo")
        session.add(PostRSVP(post_id=post_id, user_id=user_id))
        try:
            await session.commit()
            joined = True
        except IntegrityError:
            await session.rollback()
            joined = True

    count = await _rsvp_count(session, post_id)
    full = post.max_participants is not None and count >= post.max_participants
    return RsvpState(joined=joined, rsvp_count=count, rsvp_full=full)


async def list_attendees(session: AsyncSession, *, post_id: int) -> list[UserPublic]:
    """Students who clicked 'Ci sto!' on a sondaggio (for CHI_CE_STA.EXE)."""
    if await session.get(Post, post_id) is None:
        raise NotFoundError("Post not found")
    rows = await session.execute(
        select(User)
        .join(PostRSVP, PostRSVP.user_id == User.id)
        .where(PostRSVP.post_id == post_id)
        .order_by(PostRSVP.created_at)
    )
    return [UserPublic.model_validate(u) for u in rows.scalars().all()]


async def add_comment(
    session: AsyncSession, *, post_id: int, author: User, data: CommentCreate
) -> CommentOut:
    post = await session.get(Post, post_id)
    if post is None:
        raise NotFoundError("Post not found")
    reply_to: str | None = None
    if data.parent_id is not None:
        # One query validates the parent exists on THIS post and gets its author
        # login for the @ref (a reply across posts is rejected).
        reply_to = await session.scalar(
            select(User.login)
            .join(Comment, Comment.author_id == User.id)
            .where(Comment.id == data.parent_id, Comment.post_id == post_id)
        )
        if reply_to is None:
            raise NotFoundError("Parent comment not found")
    comment = Comment(
        post_id=post_id, author_id=author.id, content=data.content, parent_id=data.parent_id
    )
    session.add(comment)
    await session.commit()
    await session.refresh(comment, attribute_names=["author"])
    return _comment_out(comment, author.id, reply_to=reply_to)


async def delete_comment(session: AsyncSession, *, comment_id: int, user_id: int) -> int:
    """Delete a comment the caller owns; return its post id (for broadcasting)."""
    comment = await session.get(Comment, comment_id)
    if comment is None:
        raise NotFoundError("Comment not found")
    if comment.author_id != user_id:
        raise ForbiddenError("You can only delete your own comments")
    post_id = comment.post_id
    await session.delete(comment)
    await session.commit()
    return post_id


async def comment_count(session: AsyncSession, post_id: int) -> int:
    count = await session.scalar(
        select(func.count(Comment.id)).where(Comment.post_id == post_id)
    )
    return int(count or 0)


def _comment_out(comment: Comment, viewer_id: int, reply_to: str | None = None) -> CommentOut:
    out = CommentOut.model_validate(comment)  # picks up parent_id from the ORM row
    out.is_mine = comment.author_id == viewer_id
    out.reply_to = reply_to
    return out
