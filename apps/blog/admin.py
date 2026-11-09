from typing import Any

from django.contrib import admin
from django.db.models import Count, QuerySet
from django.http import HttpRequest, HttpResponseRedirect
from django.urls import reverse

from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import (
    AutocompleteSelectFilter,
    ChoicesDropdownFilter,
    MultipleRelatedDropdownFilter,
    RangeDateTimeFilter,
    RelatedDropdownFilter,
)
from unfold.contrib.forms.widgets import WysiwygWidget
from unfold.decorators import action, display

from apps.blog.models import Category, Comment, Post, Tag


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ["name", "slug", "posts_count_display"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        return super().get_queryset(request).annotate(posts_count=Count("posts"))

    @display(description="Posts Count", ordering="posts_count")
    def posts_count_display(self, obj: Category) -> int:
        return obj.posts_count


@admin.register(Tag)
class TagAdmin(ModelAdmin):
    list_display = ["name", "slug", "posts_count_display"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        return super().get_queryset(request).annotate(posts_count=Count("posts"))

    @display(description="Posts Count", ordering="posts_count")
    def posts_count_display(self, obj: Tag) -> int:
        return obj.posts_count


@admin.register(Comment)
class CommentAdmin(ModelAdmin):
    list_display = ["post_title_display", "author", "short_body", "created_at"]
    list_select_related = ["post", "author"]
    search_fields = ["body", "author__email", "post__title"]
    autocomplete_fields = ["post", "author"]
    list_filter_submit = True
    list_filter = [
        ("post", AutocompleteSelectFilter),
        ("author", AutocompleteSelectFilter),
        ("created_at", RangeDateTimeFilter),
    ]

    @display(description="Post Title")
    def post_title_display(self, obj: Comment) -> str:
        return obj.post.title

    @display(description="Body")
    def short_body(self, obj: Comment) -> str:
        if len(obj.body) > 50:
            return f"{obj.body[:50]}..."
        return obj.body


class CommentInline(TabularInline):
    model = Comment
    extra = 0
    tab = True
    per_page = 10
    fields = ["author", "body", "created_at"]
    readonly_fields = ["created_at"]
    autocomplete_fields = ["author"]


@admin.register(Post)
class PostAdmin(ModelAdmin):
    list_display = [
        "post_header",
        "status_label",
        "category",
        "tags_dropdown",
        "comments_count_display",
        "created_at",
    ]
    search_fields = ["title", "body", "author__email"]
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ["author", "category", "tags"]
    list_select_related = ["author", "category"]
    warn_unsaved_form = True
    inlines = [CommentInline]
    formfield_overrides = {
        Post._meta.get_field("body"): {"widget": WysiwygWidget},
    }
    list_filter_submit = True
    list_filter = [
        ("status", ChoicesDropdownFilter),
        ("category", RelatedDropdownFilter),
        ("tags", MultipleRelatedDropdownFilter),
        ("author", AutocompleteSelectFilter),
        ("created_at", RangeDateTimeFilter),
    ]

    fieldsets = (
        ("Content", {"classes": ("tab",), "fields": ("title", "slug", "body")}),
        ("Classification", {"classes": ("tab",), "fields": ("category", "tags", "status")}),
        ("Meta", {"classes": ("tab",), "fields": ("author", "created_at", "updated_at")}),
    )
    readonly_fields = ["created_at", "updated_at"]

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        return (
            super()
            .get_queryset(request)
            .prefetch_related("tags")
            .annotate(comments_count=Count("comments"))
        )

    @display(description="Post", header=True)
    def post_header(self, obj: Post) -> tuple[str, str]:
        author_email = getattr(obj.author, "email", "") or getattr(obj.author, "username", "Unknown")
        return obj.title, f"By {author_email}"

    @display(description="Status", label={"published": "success", "draft": "warning"})
    def status_label(self, obj: Post) -> tuple[str, str]:
        return obj.status, obj.get_status_display()

    @display(description="Tags", dropdown=True)
    def tags_dropdown(self, obj: Post) -> list[str]:
        return [t.name for t in obj.tags.all()]

    @display(description="Comments", ordering="comments_count")
    def comments_count_display(self, obj: Post) -> int:
        return obj.comments_count

    actions = ["action_publish_selected", "action_draft_selected"]

    @action(description="Publish selected posts")
    def action_publish_selected(self, request: HttpRequest, queryset: QuerySet) -> None:
        queryset.update(status="published")

    @action(description="Move selected posts to drafts")
    def action_draft_selected(self, request: HttpRequest, queryset: QuerySet) -> None:
        queryset.update(status="draft")

    actions_row = ["action_toggle_status"]

    @action(description="Toggle Publish Status")
    def action_toggle_status(self, request: HttpRequest, object_id: int) -> HttpResponseRedirect:
        post = self.get_object(request, object_id)
        if post:
            post.status = "draft" if post.status == "published" else "published"
            post.save()
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", ""))

    actions_list = ["action_publish_all_drafts"]

    @action(description="Publish all drafts")
    def action_publish_all_drafts(self, request: HttpRequest) -> HttpResponseRedirect:
        Post.objects.filter(status="draft").update(status="published")
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", ""))

    actions_detail = ["action_view_comments"]

    @action(description="View Post Comments")
    def action_view_comments(self, request: HttpRequest, object_id: int) -> HttpResponseRedirect:
        url = reverse("admin:blog_comment_changelist") + f"?post__id__exact={object_id}"
        return HttpResponseRedirect(url)