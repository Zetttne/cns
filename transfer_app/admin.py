from django.contrib import admin
from .models import UserProfile, Group, Batch, TransferRequest


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "role", "msnv", "created_at")
    list_filter = ("role",)
    search_fields = ("user__username", "msnv")


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "created_at")
    search_fields = ("name", "code")


class TransferInline(admin.TabularInline):
    model = TransferRequest
    extra = 0
    fields = ("msnv", "from_code", "to_code", "effective_date", "status")
    readonly_fields = ("requested_by", "approved_by", "confirmed_by", "status")


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ("batch_number", "description", "created_by", "designated_lead", "created_at")
    list_filter = ("created_at",)
    search_fields = ("batch_number", "description", "created_by__username", "designated_lead__username")
    inlines = [TransferInline]


@admin.register(TransferRequest)
class TransferRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id", "batch", "msnv", "from_code", "to_code", "effective_date",
        "is_permanent", "status", "requested_by", "approved_by", "confirmed_by",
        "created_at",
    )
    list_filter = ("status", "is_permanent", "effective_date", "created_at")
    search_fields = (
        "msnv", "from_code", "to_code",
        "requested_by__username", "approved_by__username", "confirmed_by__username",
        "batch__batch_number",
    )
    autocomplete_fields = ("batch", "requested_by", "approved_by", "confirmed_by")