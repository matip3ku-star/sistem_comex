from django.contrib import admin
from django.utils.html import format_html
from simple_history.admin import SimpleHistoryAdmin
from .models import LoteMateriaPrima, ConsumoMateriaPrima


class ConsumoInline(admin.TabularInline):
    model = ConsumoMateriaPrima
    extra = 0
    readonly_fields = ("creado_en",)
    fields = ("orden_produccion", "cantidad_consumida", "fecha_consumo", "notas", "usuario")
    ordering = ("-fecha_consumo",)


@admin.register(LoteMateriaPrima)
class LoteMateriaPrimaAdmin(SimpleHistoryAdmin):
    list_display = (
        "numero_lote",
        "producto",
        "cantidad_inicial",
        "cantidad_actual",
        "proveedor_lote",
        "fecha_ingreso",
        "tiene_certificado",
        "activo",
    )
    list_filter = ("activo", "producto", "fecha_ingreso")
    search_fields = ("numero_lote", "producto__codigo", "producto__nombre", "proveedor_lote")
    ordering = ("-fecha_ingreso",)
    readonly_fields = ("creado_en",)
    inlines = [ConsumoInline]

    @admin.display(description="Certificado", boolean=True)
    def tiene_certificado(self, obj):
        return bool(obj.certificado_calidad)


@admin.register(ConsumoMateriaPrima)
class ConsumoMateriaPrimaAdmin(admin.ModelAdmin):
    list_display = ("orden_produccion", "lote", "cantidad_consumida", "fecha_consumo", "usuario")
    list_filter = ("fecha_consumo", "lote__producto")
    search_fields = ("orden_produccion", "lote__numero_lote", "lote__producto__codigo")
    ordering = ("-fecha_consumo",)
    readonly_fields = ("creado_en",)
