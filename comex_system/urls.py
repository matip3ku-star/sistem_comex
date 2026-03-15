from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import admin_config  # noqa: F401

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.stock.urls")),
    path("", include("apps.importador.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
