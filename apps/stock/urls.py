from django.urls import path
from . import views
from . import dashboard

urlpatterns = [
    path("dashboard/", dashboard.dashboard, name="dashboard"),
    path("stock/", views.vista_stock, name="vista_stock"),
    path("stock/lotes/<int:producto_id>/", views.lotes_por_producto, name="lotes_por_producto"),
    path("stock/ajustar/<int:lote_id>/", views.ajustar_stock_lote, name="ajustar_stock_lote"),
    path("auditoria/stock/", views.log_auditoria, name="log_auditoria"),
]
