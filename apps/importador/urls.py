from django.urls import path
from . import views

urlpatterns = [
    path("importador/", views.vista_importador, name="importador"),
    path("importador/productos/", views.importar_productos, name="importar_productos"),
    path("importador/proveedores/", views.importar_proveedores, name="importar_proveedores"),
    path("importador/descargar/<str:tipo>/", views.descargar_template, name="descargar_template"),
]
