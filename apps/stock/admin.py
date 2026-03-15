from django.contrib import admin
from django.utils.html import format_html, mark_safe
from simple_history.admin import SimpleHistoryAdmin
from .models import Lote, MovimientoStock, StockConsolidado


class MovimientoInline(admin.TabularInline):
    model = MovimientoStock
    extra = 0
    readonly_fields = ("fecha_hora", "usuario", "registrado_via_qr")
    fields = ("tipo", "cantidad", "motivo", "notas", "fecha_hora", "usuario", "registrado_via_qr")
    ordering = ("-fecha_hora",)
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Lote)
class LoteAdmin(SimpleHistoryAdmin):
    list_display = (
        "numero_lote",
        "producto",
        "categoria_display",
        "cantidad_actual",
        "badge_estado",
        "fecha_ingreso",
        "esta_vencido",
        "importacion",
    )
    list_filter = (
        "categoria",
        "estado",
        ("fecha_ingreso", admin.DateFieldListFilter),
    )
    search_fields = (
        "numero_lote",
        "producto__codigo",
        "producto__nombre",
        "producto__descripcion",
        "producto__proveedor__nombre",
    )
    ordering = ("-fecha_ingreso",)
    readonly_fields = ("creado_en",)
    inlines = [MovimientoInline]
    date_hierarchy = "fecha_ingreso"

    fieldsets = (
        ("Identificación", {
            "fields": ("producto", "numero_lote", "categoria", "importacion"),
        }),
        ("Cantidades", {
            "fields": ("cantidad_inicial", "cantidad_actual", "estado"),
        }),
        ("Fechas", {
            "fields": ("fecha_ingreso", "fecha_vencimiento"),
        }),
        ("Documentación", {
            "fields": ("certificado_calidad", "observaciones"),
            "classes": ("collapse",),
        }),
        ("Auditoría", {
            "fields": ("creado_en",),
            "classes": ("collapse",),
        }),
    )

    actions = ["liberar_lotes"]

    @admin.display(description="Categoría", ordering="categoria")
    def categoria_display(self, obj):
        return obj.get_categoria_display()

    @admin.display(description="Estado", ordering="estado")
    def badge_estado(self, obj):
        colores = {
            "LIBERADO":  ("#27ae60", "Liberado"),
            "BLOQUEADO": ("#e67e22", "Bloqueado ANMAT"),
            "AGOTADO":   ("#95a5a6", "Agotado"),
        }
        color, label = colores.get(obj.estado, ("#999", obj.estado))
        return format_html(
            '<span style="color:white;background:{};padding:2px 8px;border-radius:4px;font-size:11px;">{}</span>',
            color, label,
        )

    @admin.action(description="Liberar lotes seleccionados (aprobación ANMAT manual)")
    def liberar_lotes(self, request, queryset):
        liberados = 0
        for lote in queryset.filter(estado="BLOQUEADO"):
            lote.liberar()
            liberados += 1
        self.message_user(request, f"{liberados} lote(s) liberado(s) correctamente.")


@admin.register(MovimientoStock)
class MovimientoStockAdmin(SimpleHistoryAdmin):
    list_display = ("fecha_hora", "lote", "tipo", "cantidad", "motivo", "usuario", "registrado_via_qr")
    list_filter = (
        "tipo",
        "motivo",
        "registrado_via_qr",
        ("fecha_hora", admin.DateFieldListFilter),
    )
    search_fields = ("lote__numero_lote", "lote__producto__codigo", "notas")
    ordering = ("-fecha_hora",)
    readonly_fields = ("fecha_hora",)
    date_hierarchy = "fecha_hora"

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(StockConsolidado)
class StockConsolidadoAdmin(admin.ModelAdmin):
    list_display = (
        "producto",
        "stock_disponible",
        "stock_bloqueado",
        "stock_total",
        "badge_nivel",
        "actualizado_en",
    )
    list_filter = ("producto__categoria",)
    search_fields = (
        "producto__codigo",
        "producto__nombre",
        "producto__descripcion",
        "producto__proveedor__nombre",
    )
    ordering = ("producto__codigo",)
    readonly_fields = ("actualizado_en",)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Nivel de alerta")
    def badge_nivel(self, obj):
        config = {
            "normal":   ("#27ae60", "Normal"),
            "atencion": ("#f39c12", "Atención"),
            "critico":  ("#c0392b", "Crítico"),
        }
        color, label = config.get(obj.nivel_alerta, ("#999", "—"))
        return format_html(
            '<span style="color:white;background:{};padding:2px 8px;border-radius:4px;font-size:11px;">{}</span>',
            color, label,
        )
