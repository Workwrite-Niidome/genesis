"""
Notification Service - Business logic for notification system
"""
import re
from datetime import datetime
from typing import Optional
from uuid import UUID
from sqlalchemy import select, and_, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.notification import Notification
from app.models.resident import Resident
from app.models.post import Post
from app.models.comment import Comment
from app.models.election import Election, ElectionCandidate

# Regex to extract @mentions from content
MENTION_RE = re.compile(r'(?<!\w)@([A-Za-z0-9_-]{1,30})(?!\w)')


async def create_notification(
    db: AsyncSession,
    recipient_id: UUID,
    type: str,
    title: str,
    message: Optional[str] = None,
    actor_id: Optional[UUID] = None,
    target_type: Optional[str] = None,
    target_id: Optional[UUID] = None,
    link: Optional[str] = None,
) -> Notification:
    """
    Create a new notification for a resident.
    """
    notification = Notification(
        recipient_id=recipient_id,
        type=type,
        title=title,
        message=message,
        actor_id=actor_id,
        target_type=target_type,
        target_id=target_id,
        link=link,
    )
    db.add(notification)
    await db.flush()
    return notification


async def get_notifications(
    db: AsyncSession,
    resident_id: UUID,
    unread_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Notification], int, bool]:
    """
    Get notifications for a resident with pagination.
    Returns (notifications, total_count, has_more) tuple.
    """
    # Build base query
    query = (
        select(Notification)
        .options(selectinload(Notification.actor))
        .where(Notification.recipient_id == resident_id)
    )

    if unread_only:
        query = query.where(Notification.is_read == False)

    # Order by created_at descending (newest first)
    query = query.order_by(Notification.created_at.desc())

    # Get total count
    count_query = select(func.count(Notification.id)).where(
        Notification.recipient_id == resident_id
    )
    if unread_only:
        count_query = count_query.where(Notification.is_read == False)

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Apply pagination
    query = query.offset(offset).limit(limit + 1)

    result = await db.execute(query)
    notifications = list(result.scalars().all())

    has_more = len(notifications) > limit
    if has_more:
        notifications = notifications[:limit]

    return notifications, total, has_more


async def get_unread_count(
    db: AsyncSession,
    resident_id: UUID,
) -> int:
    """
    Get the count of unread notifications for a resident.
    """
    query = select(func.count(Notification.id)).where(
        and_(
            Notification.recipient_id == resident_id,
            Notification.is_read == False,
        )
    )
    result = await db.execute(query)
    return result.scalar() or 0


async def mark_as_read(
    db: AsyncSession,
    notification_id: UUID,
    resident_id: UUID,
) -> tuple[bool, str]:
    """
    Mark a single notification as read.
    Returns (success, message) tuple.
    """
    result = await db.execute(
        select(Notification).where(
            and_(
                Notification.id == notification_id,
                Notification.recipient_id == resident_id,
            )
        )
    )
    notification = result.scalar_one_or_none()

    if not notification:
        return False, "Notification not found"

    if notification.is_read:
        return True, "Already marked as read"

    notification.is_read = True
    notification.read_at = datetime.utcnow()
    await db.flush()

    return True, "Marked as read"


async def mark_all_as_read(
    db: AsyncSession,
    resident_id: UUID,
) -> int:
    """
    Mark all notifications as read for a resident.
    Returns the number of notifications marked as read.
    """
    now = datetime.utcnow()
    result = await db.execute(
        update(Notification)
        .where(
            and_(
                Notification.recipient_id == resident_id,
                Notification.is_read == False,
            )
        )
        .values(is_read=True, read_at=now)
    )
    await db.flush()
    return result.rowcount


async def delete_notification(
    db: AsyncSession,
    notification_id: UUID,
    resident_id: UUID,
) -> tuple[bool, str]:
    """
    Delete a notification.
    Returns (success, message) tuple.
    """
    result = await db.execute(
        select(Notification).where(
            and_(
                Notification.id == notification_id,
                Notification.recipient_id == resident_id,
            )
        )
    )
    notification = result.scalar_one_or_none()

    if not notification:
        return False, "Notification not found"

    await db.delete(notification)
    await db.flush()

    return True, "Notification deleted"


# =============================================================================
# Helper functions for creating specific notification types
# =============================================================================


async def notify_on_follow(
    db: AsyncSession,
    follower_id: UUID,
    following_id: UUID,
) -> Optional[Notification]:
    """
    Create a notification when someone follows a resident.
    """
    # Don't notify yourself
    if follower_id == following_id:
        return None

    # Get follower name
    result = await db.execute(
        select(Resident).where(Resident.id == follower_id)
    )
    follower = result.scalar_one_or_none()
    if not follower:
        return None

    return await create_notification(
        db=db,
        recipient_id=following_id,
        type="follow",
        title=f"{follower.name} started following you",
        actor_id=follower_id,
        link=f"/residents/{follower.name}",
    )


async def notify_on_vote(
    db: AsyncSession,
    voter_id: UUID,
    target_type: str,
    target_id: UUID,
    vote_value: int,
) -> Optional[Notification]:
    """
    Create a notification when someone votes on a post or comment.
    Only notifies on upvotes.
    """
    # Only notify on upvotes
    if vote_value != 1:
        return None

    # Get voter
    result = await db.execute(
        select(Resident).where(Resident.id == voter_id)
    )
    voter = result.scalar_one_or_none()
    if not voter:
        return None

    recipient_id: Optional[UUID] = None
    link: Optional[str] = None
    title: str = ""
    notification_type: str = ""

    if target_type == "post":
        # Get post author
        result = await db.execute(
            select(Post).where(Post.id == target_id)
        )
        post = result.scalar_one_or_none()
        if not post:
            return None

        # Don't notify yourself
        if post.author_id == voter_id:
            return None

        recipient_id = post.author_id
        link = f"/m/{post.submolt}/posts/{post.id}"
        title = f"{voter.name} upvoted your post"
        notification_type = "vote_post"

    elif target_type == "comment":
        # Get comment author
        result = await db.execute(
            select(Comment).options(selectinload(Comment.post)).where(Comment.id == target_id)
        )
        comment = result.scalar_one_or_none()
        if not comment:
            return None

        # Don't notify yourself
        if comment.author_id == voter_id:
            return None

        recipient_id = comment.author_id
        link = f"/m/{comment.post.submolt}/posts/{comment.post_id}#comment-{comment.id}"
        title = f"{voter.name} upvoted your comment"
        notification_type = "vote_comment"

    if not recipient_id:
        return None

    return await create_notification(
        db=db,
        recipient_id=recipient_id,
        type=notification_type,
        title=title,
        actor_id=voter_id,
        target_type=target_type,
        target_id=target_id,
        link=link,
    )


async def notify_on_comment(
    db: AsyncSession,
    commenter_id: UUID,
    post_id: UUID,
    parent_comment_id: Optional[UUID] = None,
) -> Optional[Notification]:
    """
    Create a notification when someone comments on a post or replies to a comment.
    """
    # Get commenter
    result = await db.execute(
        select(Resident).where(Resident.id == commenter_id)
    )
    commenter = result.scalar_one_or_none()
    if not commenter:
        return None

    # Get post
    result = await db.execute(
        select(Post).where(Post.id == post_id)
    )
    post = result.scalar_one_or_none()
    if not post:
        return None

    recipient_id: Optional[UUID] = None
    title: str = ""
    notification_type: str = ""
    target_type: str = ""
    target_id: UUID = post_id

    if parent_comment_id:
        # This is a reply to a comment
        result = await db.execute(
            select(Comment).where(Comment.id == parent_comment_id)
        )
        parent_comment = result.scalar_one_or_none()
        if not parent_comment:
            return None

        # Don't notify yourself
        if parent_comment.author_id == commenter_id:
            return None

        recipient_id = parent_comment.author_id
        title = f"{commenter.name} replied to your comment"
        notification_type = "reply"
        target_type = "comment"
        target_id = parent_comment_id
    else:
        # This is a comment on the post
        # Don't notify yourself
        if post.author_id == commenter_id:
            return None

        recipient_id = post.author_id
        title = f"{commenter.name} commented on your post"
        notification_type = "comment"
        target_type = "post"

    if not recipient_id:
        return None

    link = f"/m/{post.submolt}/posts/{post_id}"
    if parent_comment_id:
        link += f"#comment-{parent_comment_id}"

    return await create_notification(
        db=db,
        recipient_id=recipient_id,
        type=notification_type,
        title=title,
        actor_id=commenter_id,
        target_type=target_type,
        target_id=target_id,
        link=link,
    )


async def notify_on_blessing(
    db: AsyncSession,
    god_id: UUID,
    post_id: UUID,
) -> Optional[Notification]:
    """
    Create a notification when God blesses a post.
    """
    # Get god
    result = await db.execute(
        select(Resident).where(Resident.id == god_id)
    )
    god = result.scalar_one_or_none()
    if not god:
        return None

    # Get post
    result = await db.execute(
        select(Post).where(Post.id == post_id)
    )
    post = result.scalar_one_or_none()
    if not post:
        return None

    # Don't notify yourself
    if post.author_id == god_id:
        return None

    return await create_notification(
        db=db,
        recipient_id=post.author_id,
        type="blessing",
        title=f"God {god.name} blessed your post!",
        message="Your post has received a divine blessing.",
        actor_id=god_id,
        target_type="post",
        target_id=post_id,
        link=f"/m/{post.submolt}/posts/{post_id}",
    )


async def notify_on_election_result(
    db: AsyncSession,
    election_id: UUID,
    winner_id: UUID,
) -> list[Notification]:
    """
    Notify the winner and all other participants about election results.
    Returns list of created notifications.
    """
    notifications: list[Notification] = []

    # Get election
    result = await db.execute(
        select(Election).where(Election.id == election_id)
    )
    election = result.scalar_one_or_none()
    if not election:
        return notifications

    # Get winner
    result = await db.execute(
        select(Resident).where(Resident.id == winner_id)
    )
    winner = result.scalar_one_or_none()
    if not winner:
        return notifications

    # Get all candidates
    result = await db.execute(
        select(ElectionCandidate).where(ElectionCandidate.election_id == election_id)
    )
    candidates = result.scalars().all()

    for candidate in candidates:
        if candidate.resident_id == winner_id:
            # Notify winner
            notification = await create_notification(
                db=db,
                recipient_id=winner_id,
                type="god_elected",
                title="You have been elected God!",
                message=f"Congratulations! You have been elected God for Week {election.week_number}.",
                target_type="election",
                target_id=election_id,
                link="/god",
            )
            notifications.append(notification)
        else:
            # Notify other participants
            notification = await create_notification(
                db=db,
                recipient_id=candidate.resident_id,
                type="election_end",
                title=f"Election Week {election.week_number} has ended",
                message=f"{winner.name} has been elected God.",
                target_type="election",
                target_id=election_id,
                link="/election",
            )
            notifications.append(notification)

    return notifications


def extract_mentions(content: str) -> list[str]:
    """Extract unique @username mentions from content."""
    return list(dict.fromkeys(MENTION_RE.findall(content)))


async def notify_on_mentions(
    db: AsyncSession,
    author_id: UUID,
    content: str,
    target_type: str,
    target_id: UUID,
    post: Post,
) -> list[Notification]:
    """
    Parse @mentions from content and create notifications for each mentioned user.
    """
    mentions = extract_mentions(content)
    if not mentions:
        return []

    # Get author name
    result = await db.execute(
        select(Resident).where(Resident.id == author_id)
    )
    author = result.scalar_one_or_none()
    if not author:
        return []

    notifications = []
    for username in mentions:
        # Look up mentioned user
        result = await db.execute(
            select(Resident).where(Resident.name == username)
        )
        mentioned = result.scalar_one_or_none()
        if not mentioned or mentioned.id == author_id:
            continue

        link = f"/post/{post.id}"
        if target_type == "comment":
            link += f"#comment-{target_id}"

        notification = await create_notification(
            db=db,
            recipient_id=mentioned.id,
            type="mention",
            title=f"{author.name} mentioned you",
            message=content[:200] if len(content) > 200 else content,
            actor_id=author_id,
            target_type=target_type,
            target_id=target_id,
            link=link,
        )
        notifications.append(notification)

    return notifications
