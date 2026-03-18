from django.contrib import admin
from django.utils.html import format_html, mark_safe
from simple_history.admin import SimpleHistoryAdmin
from .models import Producto, Proveedor, Sector


@admin.register(Sector)
class SectorAdmin(admin.ModelAdmin):
    list_display = ("nombre", "activo")
    search_fields = ("nombre",)
    list_filter = ("activo",)
    ordering = ("nombre",)


@admin.register(Producto)
class ProductoAdmin(SimpleHistoryAdmin):
    list_display = (
        "codigo",
        "nombre",
        "categoria",
        "proveedor",
        "badge_anmat",
        "activo",
    )
    list_filter = ("categoria", "requiere_anmat", "activo", "proveedor")
    search_fields = ("codigo", "nombre", "descripcion")
    ordering = ("codigo",)
    readonly_fields = (
        "punto_reorden_display",
        "tiempo_total_reposicion_display",
        "creado_en",
        "actualizado_en",
    )
    filter_horizontal = ()

    fieldsets = (
        ("Identificacion", {
            "fields": ("codigo", "nombre", "descripcion", "categoria", "unidad_medida"),
        }),
        ("Proveedor", {
            "fields": ("proveedor",),
        }),
        ("Regulatorio ANMAT", {
            "fields": (
                "requiere_anmat",
                "numero_registro_anmat",
                "vencimiento_habilitacion_anmat",
            ),
            "classes": ("collapse",),
        }),
        ("Parametros de planificacion", {
            "fields": (
                "stock_minimo_seguridad",
                "tiempo_transito_dias",
                "tiempo_tramite_anmat_dias",
                "tiempo_total_reposicion_display",
                "consumo_promedio_mensual",
                "consumo_manual",
                "punto_reorden_display",
            ),
            "classes": ("collapse",),
        }),
        ("Control", {
            "fields": ("activo", "creado_en", "actualizado_en"),
            "classes": ("collapse",),
        }),
    )

    @admin.display(description="ANMAT", ordering="requiere_anmat")
    def badge_anmat(self, obj):
        if obj.requiere_anmat:
            return mark_safe(
                '<span style="color:white;background:#c0392b;padding:2px 8px;'
                'border-radius:4px;font-size:11px;">Regulado</span>'
            )
        return mark_safe(
            '<span style="color:#555;background:#eee;padding:2px 8px;'
            'border-radius:4px;font-size:11px;">Libre</span>'
        )

    @admin.display(description="Sectores")
    def sectores_display(self, obj):
        sectores = obj.sectores.filter(activo=True)
        if not sectores.exists():
            return "—"
        return ", ".join(s.nombre for s in sectores)

    @admin.display(description="Punto de reorden")
    def punto_reorden_display(self, obj):
        valor = obj.punto_reorden
        if valor is None:
            return "— (sin consumo definido)"
        return f"{valor:.2f} {obj.get_unidad_medida_display()}"

    @admin.display(description="Tiempo total reposicion")
    def tiempo_total_reposicion_display(self, obj):
        return f"{obj.tiempo_total_reposicion} dias"
