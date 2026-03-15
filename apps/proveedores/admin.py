from django.contrib import admin
from django.utils.html import format_html, mark_safe
from simple_history.admin import SimpleHistoryAdmin
from .models import FichaProveedor, Comunicacion, Pago
from apps.productos.models import Proveedor


class FichaProveedorInline(admin.StackedInline):
    model = FichaProveedor
    extra = 0
    can_delete = False
    fields = (
        "contacto_nombre", "contacto_email", "contacto_whatsapp",
        "canal_habitual", "moneda_habitual", "plazo_pago_dias",
        "modalidad_pago", "notas",
    )


class ComunicacionInline(admin.TabularInline):
    model = Comunicacion
    extra = 0
    readonly_fields = ("fecha_hora", "usuario")
    fields = ("tipo", "canal", "importacion", "resumen", "adjunto", "fecha_hora", "usuario")
    ordering = ("-fecha_hora",)


class PagoInline(admin.TabularInline):
    model = Pago
    extra = 0
    readonly_fields = ("nivel_urgencia_display",)
    fields = (
        "importacion", "modalidad", "monto", "moneda",
        "fecha_vencimiento", "estado", "fecha_pago", "nivel_urgencia_display",
    )
    ordering = ("fecha_vencimiento",)

    @admin.display(description="Urgencia")
    def nivel_urgencia_display(self, obj):
        return obj.nivel_urgencia or "—"


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ("nombre", "pais_origen", "activo")
    list_filter = ("activo", "pais_origen")
    search_fields = ("nombre",)
    ordering = ("nombre",)
    inlines = [FichaProveedorInline, ComunicacionInline, PagoInline]


@admin.register(FichaProveedor)
class FichaProveedorAdmin(admin.ModelAdmin):
    list_display = (
        "proveedor", "contacto_nombre", "contacto_email",
        "canal_habitual", "moneda_habitual", "plazo_pago_dias",
    )
    search_fields = ("proveedor__nombre", "contacto_nombre", "contacto_email")
    list_filter = ("canal_habitual", "moneda_habitual")


@admin.register(Comunicacion)
class ComunicacionAdmin(admin.ModelAdmin):
    list_display = ("fecha_hora", "proveedor", "tipo", "canal", "importacion", "usuario")
    list_filter = ("tipo", "canal", "proveedor", "fecha_hora")
    search_fields = ("proveedor__nombre", "resumen", "importacion__numero_orden")
    ordering = ("-fecha_hora",)
    readonly_fields = ("creado_en",)

    fieldsets = (
        ("Comunicación", {
            "fields": ("proveedor", "importacion", "tipo", "canal", "fecha_hora"),
        }),
        ("Contenido", {
            "fields": ("resumen", "adjunto"),
        }),
        ("Auditoría", {
            "fields": ("usuario", "creado_en"),
            "classes": ("collapse",),
        }),
    )


@admin.register(Pago)
class PagoAdmin(SimpleHistoryAdmin):
    list_display = (
        "proveedor",
        "importacion",
        "monto",
        "moneda",
        "fecha_vencimiento",
        "badge_estado",
        "badge_urgencia",
        "fecha_pago",
    )
    list_filter = ("estado", "modalidad", "moneda", "proveedor")
    search_fields = (
        "proveedor__nombre",
        "importacion__numero_orden",
        "notas",
    )
    ordering = ("fecha_vencimiento",)
    readonly_fields = ("creado_en", "actualizado_en", "dias_para_vencimiento")

    fieldsets = (
        ("Pago", {
            "fields": ("proveedor", "importacion", "modalidad"),
        }),
        ("Monto", {
            "fields": ("monto", "moneda", "tipo_cambio"),
        }),
        ("Vencimiento y estado", {
            "fields": ("fecha_vencimiento", "estado", "fecha_pago", "dias_para_vencimiento"),
        }),
        ("Comprobante", {
            "fields": ("comprobante",),
        }),
        ("Notas y auditoría", {
            "fields": ("notas", "creado_por", "creado_en", "actualizado_en"),
            "classes": ("collapse",),
        }),
    )

    actions = ["marcar_pagado"]

    @admin.display(description="Estado", ordering="estado")
    def badge_estado(self, obj):
        colores = {
            "PENDIENTE": ("#e67e22", "Pendiente"),
            "PAGADO":    ("#27ae60", "Pagado"),
            "VENCIDO":   ("#c0392b", "Vencido"),
        }
        color, label = colores.get(obj.estado, ("#999", obj.estado))
        return format_html(
            '<span style="color:white;background:{};padding:2px 8px;border-radius:4px;font-size:11px;">{}</span>',
            color, label,
        )

    @admin.display(description="Urgencia")
    def badge_urgencia(self, obj):
        config = {
            "critico": ("#c0392b", "Crítico"),
            "urgente": ("#e74c3c", "Urgente"),
            "proximo": ("#e67e22", "Próximo"),
            "normal":  ("#27ae60", "Normal"),
        }
        nivel = obj.nivel_urgencia
        if nivel is None:
            return "—"
        color, label = config.get(nivel, ("#999", nivel))
        return format_html(
            '<span style="color:white;background:{};padding:2px 8px;border-radius:4px;font-size:11px;">{}</span>',
            color, label,
        )

    @admin.action(description="Registrar como pagado (fecha hoy)")
    def marcar_pagado(self, request, queryset):
        from django.utils import timezone
        for pago in queryset.filter(estado="PENDIENTE"):
            pago.registrar_pago(fecha_pago=timezone.now().date(), usuario=request.user)
        self.message_user(request, f"{queryset.count()} pago(s) registrado(s) como pagados.")
