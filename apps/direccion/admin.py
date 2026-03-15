from django.contrib import admin
from django.shortcuts import redirect
from django.urls import path
from .models import Dashboard


class DashboardAdmin(admin.ModelAdmin):
    """
    Admin que redirige directamente al dashboard
    cuando el usuario hace clic en el menu lateral.
    """

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "",
                self.admin_site.admin_view(self.redirect_dashboard),
                name="direccion_dashboard_changelist",
            ),
        ]
        return custom + urls

    def redirect_dashboard(self, request):
        return redirect("/dashboard/")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(Dashboard, DashboardAdmin)
