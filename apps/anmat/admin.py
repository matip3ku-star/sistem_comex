from django.contrib import admin
from django.utils.html import format_html, mark_safe
from django.utils import timezone
from simple_history.admin import SimpleHistoryAdmin
from .models import TramiteANMAT, CambioEstadoANMAT


class CambioEstadoANMATInline(admin.TabularInline):
    model = CambioEstadoANMAT
    extra = 0
    readonly_fields = ("estado_anterior", "estado_nuevo", "notas", "usuario", "fecha_hora")
    ordering = ("-fecha_hora",)

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(TramiteANMAT)
class TramiteANMATAdmin(SimpleHistoryAdmin):
    list_display = (
        "importacion",
        "badge_estado",
        "fecha_presentacion",
        "fecha_finalizacion",
        "badge_comprobante_vep",
        "despachante",
        "dias_en_tramite",
    )
    list_filter = ("estado", "despachante", "fecha_presentacion")
    search_fields = (
        "importacion__numero_orden",
        "numero_expediente",
        "importacion__proveedor__nombre",
    )
    ordering = ("-fecha_presentacion",)
    readonly_fields = ("creado_en", "actualizado_en", "dias_en_tramite")
    inlines = [CambioEstadoANMATInline]

    fieldsets = (
        ("Importacion vinculada", {
            "fields": ("importacion", "despachante"),
        }),
        ("Estado del tramite", {
            "fields": ("estado", "fecha_presentacion", "numero_expediente"),
        }),
        ("Documentacion", {
            "fields": ("documento_14_puntos",),
        }),
        ("Observaciones ANMAT", {
            "fields": ("observaciones_anmat", "respuesta_observaciones"),
            "classes": ("collapse",),
        }),
        ("VEP", {
            "fields": (
                "numero_vep",
                "monto_vep",
                "fecha_pago_vep",
                "comprobante_vep",
            ),
        }),
        ("Finalizacion", {
            "fields": ("fecha_finalizacion", "certificado_aprobacion"),
        }),
        ("Notas y auditoria", {
            "fields": ("notas", "creado_en", "actualizado_en"),
            "classes": ("collapse",),
        }),
    )

    actions = [
        "marcar_en_tramite",
        "marcar_observado",
        "marcar_pago_vep",
        "finalizar_tramite",
    ]

    @admin.display(description="Estado", ordering="estado")
    def badge_estado(self, obj):
        colores = {
            "PRESENTADO": ("#3498db", "Presentado"),
            "EN_TRAMITE": ("#9b59b6", "En tramite"),
            "OBSERVADO":  ("#e74c3c", "Observado"),
            "PAGO_VEP":   ("#e67e22", "Pago VEP"),
            "FINALIZADO": ("#27ae60", "Finalizado"),
            "RECHAZADO":  ("#7f8c8d", "Rechazado"),
        }
        color, label = colores.get(obj.estado, ("#999", obj.estado))
        urgente = " !" if obj.requiere_alerta_urgente else ""
        return format_html(
            '<span style="color:white;background:{};padding:2px 8px;border-radius:4px;font-size:11px;">{}{}</span>',
            color, label, urgente,
        )

    @admin.display(description="Comprobante VEP")
    def badge_comprobante_vep(self, obj):
        if not obj.numero_vep:
            return "—"
        if obj.comprobante_vep:
            return mark_safe(
                '<span style="color:white;background:#27ae60;padding:2px 8px;'
                'border-radius:4px;font-size:11px;">Adjunto</span>'
            )
        if obj.estado == "PAGO_VEP":
            return mark_safe(
                '<span style="color:white;background:#e74c3c;padding:2px 8px;'
                'border-radius:4px;font-size:11px;">Faltante</span>'
            )
        return mark_safe(
            '<span style="color:#888;background:#f0f0f0;padding:2px 8px;'
            'border-radius:4px;font-size:11px;">Sin cargar</span>'
        )

    @admin.display(description="Dias en tramite")
    def dias_en_tramite(self, obj):
        fin = obj.fecha_finalizacion or timezone.now().date()
        return f"{(fin - obj.fecha_presentacion).days} dias"

    def _cambiar_estado(self, request, queryset, estado_nuevo, notas=""):
        for tramite in queryset:
            estado_anterior = tramite.estado
            tramite.estado = estado_nuevo
            tramite.save(update_fields=["estado", "actualizado_en"])
            CambioEstadoANMAT.objects.create(
                tramite=tramite,
                estado_anterior=estado_anterior,
                estado_nuevo=estado_nuevo,
                usuario=request.user,
                notas=notas or "Cambio manual desde el panel de administracion",
            )
        self.message_user(request, f"{queryset.count()} tramite(s) actualizado(s).")

    @admin.action(description="Marcar como En tramite")
    def marcar_en_tramite(self, request, queryset):
        self._cambiar_estado(request, queryset, "EN_TRAMITE")

    @admin.action(description="Marcar como Observado")
    def marcar_observado(self, request, queryset):
        self._cambiar_estado(request, queryset, "OBSERVADO")

    @admin.action(description="Marcar como Pago VEP faltante")
    def marcar_pago_vep(self, request, queryset):
        self._cambiar_estado(request, queryset, "PAGO_VEP")

    @admin.action(description="Finalizar tramite y liberar lotes")
    def finalizar_tramite(self, request, queryset):
        finalizados = 0
        for tramite in queryset.exclude(estado="FINALIZADO"):
            tramite.finalizar(fecha_finalizacion=timezone.now().date(), usuario=request.user)
            finalizados += 1
        self.message_user(
            request,
            f"{finalizados} tramite(s) finalizado(s). Lotes liberados automaticamente.",
        )
