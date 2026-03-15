from django.contrib import admin
from django.utils.html import format_html
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
        ("Importación vinculada", {
            "fields": ("importacion", "despachante"),
        }),
        ("Estado del trámite", {
            "fields": ("estado", "fecha_presentacion", "numero_expediente"),
        }),
        ("Documentación", {
            "fields": ("documento_14_puntos",),
        }),
        ("Observaciones ANMAT", {
            "fields": ("observaciones_anmat", "respuesta_observaciones"),
            "classes": ("collapse",),
        }),
        ("VEP", {
            "fields": ("numero_vep", "monto_vep", "fecha_pago_vep"),
            "classes": ("collapse",),
        }),
        ("Finalización", {
            "fields": ("fecha_finalizacion", "certificado_aprobacion"),
        }),
        ("Notas y auditoría", {
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
            "PRESENTADO":  ("#3498db", "Presentado"),
            "EN_TRAMITE":  ("#9b59b6", "En trámite"),
            "OBSERVADO":   ("#e74c3c", "Observado"),
            "PAGO_VEP":    ("#e67e22", "Pago VEP"),
            "FINALIZADO":  ("#27ae60", "Finalizado"),
            "RECHAZADO":   ("#7f8c8d", "Rechazado"),
        }
        color, label = colores.get(obj.estado, ("#999", obj.estado))
        urgente = obj.requiere_alerta_urgente
        icono = " ⚠" if urgente else ""
        return format_html(
            '<span style="color:white;background:{};padding:2px 8px;border-radius:4px;font-size:11px;">{}{}</span>',
            color, label, icono,
        )

    @admin.display(description="Días en trámite")
    def dias_en_tramite(self, obj):
        fin = obj.fecha_finalizacion or timezone.now().date()
        return f"{(fin - obj.fecha_presentacion).days} días"

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
                notas=notas or f"Cambio manual desde el panel de administración",
            )
        self.message_user(request, f"{queryset.count()} trámite(s) actualizado(s).")

    @admin.action(description="Marcar como En trámite")
    def marcar_en_tramite(self, request, queryset):
        self._cambiar_estado(request, queryset, "EN_TRAMITE")

    @admin.action(description="Marcar como Observado ⚠")
    def marcar_observado(self, request, queryset):
        self._cambiar_estado(request, queryset, "OBSERVADO")

    @admin.action(description="Marcar como Pago VEP faltante ⚠")
    def marcar_pago_vep(self, request, queryset):
        self._cambiar_estado(request, queryset, "PAGO_VEP")

    @admin.action(description="✅ Finalizar trámite y liberar stock")
    def finalizar_tramite(self, request, queryset):
        finalizados = 0
        for tramite in queryset.exclude(estado="FINALIZADO"):
            tramite.finalizar(fecha_finalizacion=timezone.now().date(), usuario=request.user)
            finalizados += 1
        self.message_user(
            request,
            f"{finalizados} trámite(s) finalizado(s). Stock liberado automáticamente.",
        )
