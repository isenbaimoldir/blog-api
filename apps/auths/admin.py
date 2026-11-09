from typing import Any

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.db.models import Count, QuerySet
from django.http import HttpRequest

from unfold.admin import ModelAdmin
from unfold.contrib.filters.admin import BooleanRadioFilter
from unfold.decorators import action, display

User = get_user_model()

admin.site.unregister(Group)


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass

@admin.display(description="User")
def user_header(self, obj):
    if hasattr(obj, "get_full_name"):
        name = obj.get_full_name()
    else:
        name = getattr(obj, "email", str(obj))
    
    return name or "No Name"

@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    list_display = ["user_header", "is_active_label", "is_staff_label", "posts_count_display"]
    search_fields = ["email", "first_name", "last_name"]
    ordering = ["email"]
    list_filter = [
        ("is_active", BooleanRadioFilter),
        ("is_staff", BooleanRadioFilter),
    ]

    fieldsets = (
        ("Personal info", {"classes": ("tab",), "fields": ("first_name", "last_name", "email")}),
        ("Permissions", {"classes": ("tab",), "fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"classes": ("tab",), "fields": ("last_login", "date_joined")}),
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        return super().get_queryset(request).annotate(posts_count=Count("posts"))

    @display(description="User", header=True)
    def user_header(self, obj: User) -> tuple[str, str, str]:
        full_name = obj.get_full_name() or "No Name"
        initials = "".join([part[0].upper() for part in full_name.split()[:2]]) or "U"
        return full_name, obj.email or obj.username, initials

    @display(description="Active", label={True: "success", False: "danger"})
    def is_active_label(self, obj: User) -> tuple[bool, str]:
        return obj.is_active, "Active" if obj.is_active else "Inactive"

    @display(description="Staff", label={True: "info", False: "warning"})
    def is_staff_label(self, obj: User) -> tuple[bool, str]:
        return obj.is_staff, "Staff" if obj.is_staff else "Regular User"

    @display(description="Posts Count", ordering="posts_count")
    def posts_count_display(self, obj: User) -> int:
        return obj.posts_count

    actions = ["action_activate_users", "action_deactivate_users"]

    @action(description="Activate selected users")
    def action_activate_users(self, request: HttpRequest, queryset: QuerySet) -> None:
        queryset.update(is_active=True)

    @action(description="Deactivate selected users")
    def action_deactivate_users(self, request: HttpRequest, queryset: QuerySet) -> None:
        queryset.update(is_active=False)