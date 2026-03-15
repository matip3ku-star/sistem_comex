from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ("username", "get_full_name", "email", "rol", "telegram_chat_id", "is_active")
    list_filter = ("rol", "is_active", "is_staff")
    search_fields = ("username", "first_name", "last_name", "email")
    ordering = ("username",)

    fieldsets = UserAdmin.fieldsets + (
        ("Datos COMEX", {
            "fields": ("rol", "telefono", "telegram_chat_id"),
        }),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Datos COMEX", {
            "fields": ("rol", "telefono", "telegram_chat_id"),
        }),
    )
