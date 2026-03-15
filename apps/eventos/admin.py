from django.contrib import admin
from django.utils.html import format_html, mark_safe
from django.utils import timezone
from .models import EventoExtraordinario, AlertaProveedor


@admin.register(EventoExtraordinario)
class EventoExtraordinarioAdmin(admin.ModelAdmin):
    list_display = (
        "fecha_evento",
        "importacion",
        "proveedor_nombre",
        "tipo",
        "impacto_dias",
        "badge_patron",
        "parametro_ajustado",
        "usuario",
    )
    list_filter = ("tipo", "alerta_patron_generada", "parametro_ajustado", "fecha_evento")
    search_fields = (
        "importacion__numero_orden",
        "importacion__proveedor__nombre",
        "descripcion",
    )
    ordering = ("-fecha_evento",)
    readonly_fields = ("alerta_patron_generada", "creado_en", "proveedor_display")
    autocomplete_fields = ["importacion"]

    fieldsets = (
        ("Orden de importacion", {
            "fields": ("importacion", "proveedor_display"),
        }),
        ("Evento", {
            "fields": ("tipo", "fecha_evento", "descripcion", "impacto_dias"),
        }),
        ("Patron detectado", {
            "fields": ("alerta_patron_generada", "parametro_ajustado", "notas_ajuste"),
        }),
        ("Auditoria", {
            "fields": ("usuario", "creado_en"),
            "classes": ("collapse",),
        }),
    )

    actions = ["marcar_parametro_ajustado"]

    @admin.display(description="Proveedor")
    def proveedor_nombre(self, obj):
        return obj.importacion.proveedor.nombre

    @admin.display(description="Proveedor")
    def proveedor_display(self, obj):
        if obj.pk:
            return format_html(
                '<strong>{}</strong> ({})',
                obj.importacion.proveedor.nombre,
                obj.importacion.proveedor.pais_origen,
            )
        return "—"

    @admin.display(description="Patron")
    def badge_patron(self, obj):
        if obj.alerta_patron_generada:
            return mark_safe(
                '<span style="color:white;background:#e74c3c;padding:2px 8px;'
                'border-radius:4px;font-size:11px;">Alerta generada</span>'
            )
        return "—"

    @admin.action(description="Marcar parametros como ajustados")
    def marcar_parametro_ajustado(self, request, queryset):
        actualizados = queryset.filter(alerta_patron_generada=True).update(
            parametro_ajustado=True
        )
        self.message_user(request, f"{actualizados} evento(s) marcado(s) como ajustados.")


@admin.register(AlertaProveedor)
class AlertaProveedorAdmin(admin.ModelAdmin):
    list_display = (
        "creado_en",
        "proveedor",
        "tipo_evento",
        "cantidad_eventos",
        "badge_estado",
        "resuelta_por",
    )
    list_filter = ("resuelta", "tipo_evento", "proveedor")
    search_fields = ("proveedor__nombre", "mensaje")
    ordering = ("resuelta", "-creado_en")
    readonly_fields = ("creado_en", "resuelta_en", "resuelta_por", "cantidad_eventos")

    fieldsets = (
        ("Alerta", {
            "fields": ("proveedor", "tipo_evento", "cantidad_eventos", "mensaje", "creado_en"),
        }),
        ("Resolucion", {
            "fields": ("resuelta", "notas_resolucion", "resuelta_por", "resuelta_en"),
        }),
    )

    actions = ["resolver_alertas"]

    @admin.display(description="Estado")
    def badge_estado(self, obj):
        if obj.resuelta:
            return mark_safe(
                '<span style="color:white;background:#27ae60;padding:2px 8px;'
                'border-radius:4px;font-size:11px;">Resuelta</span>'
            )
        return mark_safe(
            '<span style="color:white;background:#e74c3c;padding:2px 8px;'
            'border-radius:4px;font-size:11px;">Pendiente</span>'
        )

    @admin.action(description="Marcar alertas seleccionadas como resueltas")
    def resolver_alertas(self, request, queryset):
        for alerta in queryset.filter(resuelta=False):
            alerta.resolver(usuario=request.user)
        self.message_user(request, f"{queryset.count()} alerta(s) marcada(s) como resuelta(s).")
