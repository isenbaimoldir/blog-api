from collections.abc import Callable
from datetime import date, datetime, timedelta
from typing import Any

from django.contrib.auth import get_user_model
from django.db.models import Avg, Case, CharField,Count,Exists,F,Max,Min, OuterRef, Prefetch, Q, QuerySet, Subquery, Value, When

from django.db.models.functions import Coalesce, Concat, TruncMonth
from django.utils import timezone
from django.utils.text import slugify

from apps.blog.models import Category, Comment, Post, Tag

User = get_user_model()

LIMIT = 5
POPULAR_AUTHOR_LIMIT = 5
PAGE_SIZE = 10
COMMENTS_LIMIT = 50
TAGGED_POSTS_LIMIT = 20
TOP_COMMENTS_LIMIT = 10
NORMAL_COMMENTS_LIMIT = 3
EDITED_TIME_PERIOD = timedelta(hours=1)
UNCATEGORIZED_LIMIT = "Uncategorized"
POPULARITY_TRENDING = "hot"
POPULARITY_AVERAGE = "normal"
POPULARITY_LOW = "quiet"


def categories_by_name() -> QuerySet[Category]:
    """Get all categories sorted by name A to Z."""
    return Category.objects.order_by("name")


def published_posts() -> QuerySet[Post]:
    """Get published posts sorted newest first."""
    return Post.objects.filter(status=Post.StatusChoices.PUBLISHED).order_by(
        "-created_at"
    )


def newest_published_posts() -> QuerySet[Post]:
    """Get the 5 newest published posts."""
    return published_posts()[:LIMIT]


def post_by_slug(slug: str) -> Post | None:
    """Get post by slug or None if not found."""
    return Post.objects.filter(slug=slug).first()


def active_users_count() -> int:
    """Count active non-staff users."""
    return User.objects.filter(is_active=True, is_staff=False).count()


def has_drafts() -> bool:
    """Check if at least one draft post exists."""
    return Post.objects.filter(status=Post.StatusChoices.DRAFT).exists()


def published_posts_page(page: int) -> QuerySet[Post]:
    """Get one page of published posts."""
    start: int = max(0, (page - 1) * PAGE_SIZE)
    end: int = start + PAGE_SIZE
    return published_posts()[start:end]


def posts_with_word_in_title(word: str) -> QuerySet[Post]:
    """Get posts whose title contains word."""
    return Post.objects.filter(title__icontains=word)


def users_with_email_domain(domain: str) -> QuerySet[User]:
    """Get users whose email ends with @domain."""
    return User.objects.filter(email__iendswith=f"@{domain}")


def posts_without_category() -> QuerySet[Post]:
    """Get posts that have no category."""
    return Post.objects.filter(category__isnull=True)


def categories_by_slugs(slugs: list[str]) -> QuerySet[Category]:
    """Get categories whose slug is in slugs."""
    return Category.objects.filter(slug__in=slugs)


def posts_in_month(year: int, month: int) -> QuerySet[Post]:
    """Get posts created in the given year and month."""
    return Post.objects.filter(created_at__year=year, created_at__month=month)


def posts_last_days(days: int) -> QuerySet[Post]:
    """Get posts created in the last days days."""
    cutoff: datetime = timezone.now() - timedelta(days=days)
    return Post.objects.filter(created_at__gte=cutoff)


def posts_between(start: date, end: date) -> QuerySet[Post]:
    """Get posts created between start and end dates inclusive."""
    return Post.objects.filter(created_at__date__range=(start, end))


def author_published_posts(email: str) -> QuerySet[Post]:
    """Get published posts by author email."""
    return Post.objects.filter(
        status=Post.StatusChoices.PUBLISHED,
        author__email__iexact=email,
    )


def posts_with_tag(tag_slug: str) -> QuerySet[Post]:
    """Get posts that have the tag with tag_slug."""
    return Post.objects.filter(tags__slug=tag_slug)


def comments_in_category(category_slug: str) -> QuerySet[Comment]:
    """Get comments on posts in the given category."""
    return Comment.objects.filter(post__category__slug=category_slug)


def users_with_published_posts() -> QuerySet[User]:
    """Get unique users who have at least one published post."""
    return User.objects.filter(posts__status=Post.StatusChoices.PUBLISHED).distinct()


def posts_without_tags() -> QuerySet[Post]:
    """Get posts that have no tags."""
    return Post.objects.filter(tags__isnull=True)


def users_without_comments() -> QuerySet[User]:
    """Get users who have never written a comment."""
    return User.objects.filter(comments__isnull=True)


def posts_with_both_tags(first_slug: str, second_slug: str) -> QuerySet[Post]:
    """Get posts that have both tags."""
    return Post.objects.filter(tags__slug=first_slug).filter(tags__slug=second_slug)


def search_posts(text: str) -> QuerySet[Post]:
    """Search posts by text in title or body."""
    return Post.objects.filter(Q(title__icontains=text) | Q(body__icontains=text))


def published_posts_missing_info() -> QuerySet[Post]:
    """Get distinct published posts missing category or tags."""
    return (
        Post.objects.filter(status=Post.StatusChoices.PUBLISHED)
        .filter(Q(category__isnull=True) | Q(tags__isnull=True))
        .distinct()
    )


def edited_posts() -> QuerySet[Post]:
    """Get posts edited more than 1 hour after creation."""
    return Post.objects.filter(updated_at__gt=F("created_at") + EDITED_TIME_PERIOD)


def comments_by_post_author() -> QuerySet[Comment]:
    """Get comments written by the author of the post."""
    return Comment.objects.filter(author=F("post__author"))


def comments_before_post() -> QuerySet[Comment]:
    """Get comments created before their post."""
    return Comment.objects.filter(created_at__lt=F("post__created_at"))


def published_authors_emails() -> list[str]:
    """Get unique sorted emails of authors with published posts."""
    return list(
        Post.objects.filter(status=Post.StatusChoices.PUBLISHED)
        .values_list("author__email", flat=True)
        .distinct()
        .order_by("author__email")
    )


def published_posts_overview() -> list[dict[str, Any]]:
    """Get overview dicts for published posts."""
    return list(
        Post.objects.filter(status=Post.StatusChoices.PUBLISHED).values(
            "title",
            author_email=F("author__email"),
            category_name=Coalesce("category__name", Value(UNCATEGORIZED_LIMIT)),
        )
    )


def posts_stats() -> dict[str, Any]:
    """Get summary statistics for all posts."""
    return Post.objects.aggregate(
        total=Count("id"),
        published=Count("id", filter=Q(status=Post.StatusChoices.PUBLISHED)),
        drafts=Count("id", filter=Q(status=Post.StatusChoices.DRAFT)),
        first_post_at=Min("created_at"),
        last_post_at=Max("created_at"),
    )


def average_comments_per_post() -> float:
    """Get average comments per published post."""
    data: dict[str, Any] = (
        Post.objects.filter(status=Post.StatusChoices.PUBLISHED)
        .annotate(comment_count=Count("comments"))
        .aggregate(avg_comments=Avg("comment_count"))
    )
    avg_value: float | None = data["avg_comments"]
    return round(float(avg_value), 2) if avg_value is not None else 0.0


def categories_with_post_count() -> QuerySet[Category]:
    """Get all categories annotated with post_count."""
    return Category.objects.annotate(post_count=Count("posts")).order_by(
        "-post_count", "name"
    )


def categories_with_published_count() -> QuerySet[Category]:
    """Get all categories annotated with published_count."""
    return Category.objects.annotate(
        published_count=Count(
            "posts", filter=Q(posts__status=Post.StatusChoices.PUBLISHED)
        )
    )


def top_authors() -> QuerySet[User]:
    """Get top 5 users by published post count."""
    return User.objects.annotate(
        published_count=Count(
            "posts", filter=Q(posts__status=Post.StatusChoices.PUBLISHED)
        )
    ).order_by("-published_count")[:POPULAR_AUTHOR_LIMIT]


def popular_tags(min_posts: int) -> QuerySet[Tag]:
    """Get tags used in at least min_posts posts."""
    return Tag.objects.annotate(post_count=Count("posts")).filter(
        post_count__gte=min_posts
    )


def posts_per_status() -> list[dict[str, Any]]:
    """Get number of posts for each status."""
    return list(
        Post.objects.values("status").annotate(count=Count("id")).order_by("status")
    )


def users_activity() -> QuerySet[User]:
    """Get users annotated with post_count and comment_count."""
    return User.objects.annotate(
        post_count=Count("posts", distinct=True),
        comment_count=Count("comments", distinct=True),
    )


def search_users_by_full_name(text: str) -> QuerySet[User]:
    """Search users by full name substring."""
    return User.objects.annotate(
        full_name=Concat("first_name", Value(" "), "last_name")
    ).filter(full_name__icontains=text)


def published_posts_per_month() -> list[dict[str, Any]]:
    """Get published post counts per month oldest first."""
    return list(
        Post.objects.filter(status=Post.StatusChoices.PUBLISHED)
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(count=Count("id"))
        .order_by("month")
    )


def posts_with_popularity() -> QuerySet[Post]:
    """Get posts annotated with comment_count and popularity label."""
    return Post.objects.annotate(comment_count=Count("comments")).annotate(
        popularity=Case(
            When(
                comment_count__gte=TOP_COMMENTS_LIMIT,
                then=Value(POPULARITY_TRENDING),
            ),
            When(
                comment_count__gte=NORMAL_COMMENTS_LIMIT,
                then=Value(POPULARITY_AVERAGE),
            ),
            default=Value(POPULARITY_LOW),
            output_field=CharField(),
        )
    )


def get_or_create_tag(name: str) -> tuple[Tag, bool]:
    tag_slug: str = slugify(name)
    return Tag.objects.get_or_create(slug=tag_slug, defaults={"name": name})


def publish_old_drafts(days: int) -> int:
    now: datetime = timezone.now()
    cutoff: datetime = now - timedelta(days=days)
    return Post.objects.filter(
        status=Post.StatusChoices.DRAFT,
        created_at__lt=cutoff,
    ).update(status=Post.StatusChoices.PUBLISHED, updated_at=now)


def tag_category_posts(category_slug: str, tag_slug: str) -> int:
    tag: Tag = Tag.objects.get(slug=tag_slug)
    posts: QuerySet[Post] = Post.objects.filter(category__slug=category_slug)
    tag.posts.add(*posts)
    return posts.count()


def merge_categories(source_slug: str, target_slug: str) -> int:
    source: Category = Category.objects.get(slug=source_slug)
    target: Category = Category.objects.get(slug=target_slug)
    moved_cnt: int = Post.objects.filter(category=source).update(category=target)
    source.delete()
    return moved_cnt


def delete_inactive_users_comments() -> int:
    deleted_cnt: int
    deleted_cnt, _ = Comment.objects.filter(author__is_active=False).delete()
    return deleted_cnt


def published_feed() -> list[str]:
    posts: QuerySet[Post] = (
        Post.objects.filter(status=Post.StatusChoices.PUBLISHED)
        .select_related("author", "category")
        .order_by("-created_at")[:COMMENTS_LIMIT]
    )
    post: Post
    return [
        f"{post.title} | {post.author.email} | "
        f"{post.category.name if post.category else UNCATEGORIZED_LIMIT}"
        for post in posts
    ]


def newest_posts_with_tags() -> list[str]:
    posts: QuerySet[Post] = Post.objects.prefetch_related("tags").order_by(
        "-created_at"
    )[:TAGGED_POSTS_LIMIT]
    post: Post
    return [
        f"{post.title}: {', '.join(tag.name for tag in post.tags.all())}"
        for post in posts
    ]


def categories_with_published_posts() -> dict[str, list[str]]:
    published_qs: QuerySet[Post] = Post.objects.filter(
        status=Post.StatusChoices.PUBLISHED
    ).order_by("-created_at")
    categories: QuerySet[Category] = Category.objects.prefetch_related(
        Prefetch("posts", queryset=published_qs, to_attr="published_posts_list")
    )
    category: Category
    return {
        category.name: [post.title for post in category.published_posts_list]
        for category in categories
    }


def posts_with_last_comment() -> QuerySet[Post]:
    last_comment_sq: QuerySet[Comment] = (
        Comment.objects.filter(post=OuterRef("pk"))
        .order_by("-created_at")
        .values("body")[:1]
    )
    return Post.objects.filter(status=Post.StatusChoices.PUBLISHED).annotate(
        last_comment=Subquery(last_comment_sq)
    )


def posts_with_staff_comments() -> QuerySet[Post]:
    staff_comments_sq: QuerySet[Comment] = Comment.objects.filter(
        post=OuterRef("pk"),
        author__is_staff=True,
    )
    return Post.objects.filter(Exists(staff_comments_sq))


def users_with_draft_as_latest_post() -> QuerySet[User]:
    latest_status_sq: QuerySet[Post] = (
        Post.objects.filter(author=OuterRef("pk"))
        .order_by("-created_at")
        .values("status")[:1]
    )
    return User.objects.annotate(
        latest_post_status=Subquery(latest_status_sq)
    ).filter(latest_post_status=Post.StatusChoices.DRAFT)


QUERIES: dict[int, Callable[..., Any]] = {
    1: categories_by_name,
    2: published_posts,
    3: newest_published_posts,
    4: post_by_slug,
    5: active_users_count,
    6: has_drafts,
    7: published_posts_page,
    8: posts_with_word_in_title,
    9: users_with_email_domain,
    10: posts_without_category,
    11: categories_by_slugs,
    12: posts_in_month,
    13: posts_last_days,
    14: posts_between,
    15: author_published_posts,
    16: posts_with_tag,
    17: comments_in_category,
    18: users_with_published_posts,
    19: posts_without_tags,
    20: users_without_comments,
    21: posts_with_both_tags,
    22: search_posts,
    23: published_posts_missing_info,
    24: edited_posts,
    25: comments_by_post_author,
    26: comments_before_post,
    27: published_authors_emails,
    28: published_posts_overview,
    29: posts_stats,
    30: average_comments_per_post,
    31: categories_with_post_count,
    32: categories_with_published_count,
    33: top_authors,
    34: popular_tags,
    35: posts_per_status,
    36: users_activity,
    37: search_users_by_full_name,
    38: published_posts_per_month,
    39: posts_with_popularity,
    40: get_or_create_tag,
    41: publish_old_drafts,
    42: tag_category_posts,
    43: merge_categories,
    44: delete_inactive_users_comments,
    45: published_feed,
    46: newest_posts_with_tags,
    47: categories_with_published_posts,
    48: posts_with_last_comment,
    49: posts_with_staff_comments,
    50: users_with_draft_as_latest_post,
}