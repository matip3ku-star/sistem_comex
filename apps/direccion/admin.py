from django.contrib import admin
from django.shortcuts import redirect, render
from django.urls import path
from django.http import HttpResponseForbidden
from .models import Dashboard

CONTRASENA_RESET = "gabriel1234"


class DashboardAdmin(admin.ModelAdmin):
    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "",
                self.admin_site.admin_view(self.redirect_dashboard),
                name="direccion_dashboard_changelist",
            ),
            path(
                "reset-demo/",
                self.admin_site.admin_view(self.vista_reset_demo),
                name="direccion_reset_demo",
            ),
        ]
        return custom + urls

    def redirect_dashboard(self, request):
        return redirect("/dashboard/")

    def vista_reset_demo(self, request):
        if not (request.user.is_superuser or getattr(request.user, "rol", None) == "ADMIN"):
            return HttpResponseForbidden("Acceso denegado.")

        contexto = {
            **self.admin_site.each_context(request),
            "title": "Reset de datos de demo",
            "error": None,
            "completado": False,
            "resumen": [],
        }

        if request.method == "POST":
            clave = request.POST.get("contrasena", "")
            confirmacion = request.POST.get("confirmacion", "")

            if clave != CONTRASENA_RESET:
                contexto["error"] = "Contrasena incorrecta."
                return render(request, "admin/direccion/reset_demo.html", contexto)

            if confirmacion.strip().upper() != "SI":
                contexto["error"] = "Debes escribir SI para confirmar."
                return render(request, "admin/direccion/reset_demo.html", contexto)

            resumen = self._ejecutar_reset()
            contexto["completado"] = True
            contexto["resumen"] = resumen
            return render(request, "admin/direccion/reset_demo.html", contexto)

        return render(request, "admin/direccion/reset_demo.html", contexto)

    def _ejecutar_reset(self):
        from apps.eventos.models import EventoExtraordinario, AlertaProveedor
        from apps.proveedores.models import FichaProveedor, Comunicacion, Pago
        from apps.anmat.models import TramiteANMAT, CambioEstadoANMAT
        from apps.stock.models import Lote, MovimientoStock, StockConsolidado
        from apps.importaciones.models import Importacion, ItemImportacion, CambioEstadoImportacion
        from apps.planificacion.models import ProyeccionAgotamiento
        from apps.productos.models import Producto, Proveedor
        from django.contrib.auth import get_user_model

        Usuario = get_user_model()
        resumen = []

        pasos = [
            ("Eventos extraordinarios",      EventoExtraordinario),
            ("Alertas de proveedor",          AlertaProveedor),
            ("Comunicaciones",                Comunicacion),
            ("Pagos",                         Pago),
            ("Cambios de estado ANMAT",       CambioEstadoANMAT),
            ("Tramites ANMAT",                TramiteANMAT),
            ("Movimientos de stock",          MovimientoStock),
            ("Stock consolidado",             StockConsolidado),
            ("Lotes",                         Lote),
            ("Items de importacion",          ItemImportacion),
            ("Cambios de estado importacion", CambioEstadoImportacion),
            ("Importaciones",                 Importacion),
            ("Proyecciones de agotamiento",   ProyeccionAgotamiento),
            ("Fichas de proveedor",           FichaProveedor),
            ("Productos",                     Producto),
            ("Proveedores",                   Proveedor),
        ]

        for nombre, modelo in pasos:
            count = modelo.objects.count()
            modelo.objects.all().delete()
            resumen.append({"nombre": nombre, "count": count})

        usuarios_prueba = ["comex01", "deposito01", "deposito02", "direccion01"]
        count_u = Usuario.objects.filter(username__in=usuarios_prueba).count()
        Usuario.objects.filter(username__in=usuarios_prueba).delete()
        resumen.append({"nombre": "Usuarios de prueba", "count": count_u})

        return resumen

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(Dashboard, DashboardAdmin)
