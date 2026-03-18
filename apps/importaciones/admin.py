from django.contrib import admin
from django.utils.html import format_html, mark_safe
from django.urls import path, reverse
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.template.response import TemplateResponse
from django.http import JsonResponse
from simple_history.admin import SimpleHistoryAdmin
from .models import Importacion, ItemImportacion, LoteImportacion, CambioEstadoImportacion, RequisitoCalidadImportacion


class RequisitoCalidadImportacionInline(admin.TabularInline):
    model = RequisitoCalidadImportacion
    extra = 1
    fields = ("tipo", "descripcion", "archivo", "vigente", "fecha_carga")
    readonly_fields = ("fecha_carga",)
    verbose_name = "Requisito de Calidad"
    verbose_name_plural = "Requisitos de Calidad"


class LoteImportacionInline(admin.TabularInline):
    model = LoteImportacion
    extra = 1
    fields = (
        "numero_lote",
        "cantidad_inicial",
        "cantidad_actual",
        "estado",
        "fecha_ingreso",
        "fecha_vencimiento",
        "certificado_calidad",
        "observaciones",
    )


class ItemImportacionInline(admin.TabularInline):
    model = ItemImportacion
    extra = 1
    fields = ("producto", "cantidad_ordenada", "cantidad_recibida", "precio_unitario_usd", "ver_lotes")
    readonly_fields = ("ver_lotes",)
    show_change_link = False

    @admin.display(description="Lotes")
    def ver_lotes(self, obj):
        if not obj.pk:
            return "—"
        count = obj.lotes.count()
        url = reverse("admin:importaciones_itemimportacion_change", args=[obj.pk])
        return format_html(
            '<a href="{}" style="padding:3px 8px;background:#6c757d;color:white;'
            'border-radius:4px;font-size:11px;text-decoration:none;">'
            'Ver lotes ({})</a>',
            url, count
        )


class CambioEstadoInline(admin.TabularInline):
    model = CambioEstadoImportacion
    extra = 0
    readonly_fields = ("estado_anterior", "estado_nuevo", "notas", "usuario", "fecha_hora")
    ordering = ("-fecha_hora",)

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ItemImportacion)
class ItemImportacionAdmin(admin.ModelAdmin):
    list_display = ("importacion", "producto", "cantidad_ordenada", "cantidad_recibida")
    search_fields = ("importacion__numero_orden", "producto__codigo", "producto__nombre")
    inlines = [LoteImportacionInline]

    def has_add_permission(self, request):
        return False


@admin.register(Importacion)
class ImportacionAdmin(SimpleHistoryAdmin):
    list_display = (
        "btn_productos",
        "numero_orden",
        "proveedor",
        "sector_destino",
        "badge_estado",
        "badge_requiere_anmat",
        "badge_despacho",
        "fecha_orden",
        "fecha_eta",
        "costo_estimado_usd",
        "btn_cambiar_estado",
    )
    list_filter = ()
    search_fields = (
        "numero_orden",
        "proveedor__nombre",
        "estado",
        "numero_tracking",
        "numero_proforma",
        "numero_bl",
        "numero_despacho",
        "item_set__producto__codigo",
        "item_set__producto__nombre",
    )
    ordering = ("-fecha_orden",)
    readonly_fields = ("creado_en", "actualizado_en", "alerta_despacho_pendiente")
    inlines = [ItemImportacionInline, RequisitoCalidadImportacionInline]

    fieldsets = (
        ("Identificacion", {
            "fields": (
                "numero_orden",
                "proveedor",
                "estado",
                "numero_proforma",
                "proforma",
            ),
        }),
        ("Sector destino", {
            "fields": (
                "sector_destino",
                "responsable_sector",
                "fecha_entrega_sector",
                "notas_sector",
            ),
        }),
        ("Fechas y Tracking", {
            "fields": (
                "fecha_orden",
                "fecha_embarque",
                "fecha_eta",
                "fecha_recepcion",
                "numero_tracking",
                "referencia_embarque",
                "numero_bl",
                "guia_transporte",
            ),
        }),
        ("Despacho aduanero", {
            "fields": (
                "numero_despacho",
                "fecha_despacho",
                "despacho",
                "alerta_despacho_pendiente",
            ),
        }),
        ("Responsables", {
            "fields": ("despachante", "creado_por"),
        }),
        ("Financiero", {
            "fields": ("costo_estimado_usd", "moneda"),
        }),
        ("Notas", {
            "fields": ("notas",),
            "classes": ("collapse",),
        }),
        ("Auditoria", {
            "fields": ("creado_en", "actualizado_en"),
            "classes": ("collapse",),
        }),
    )

    actions = [
        "marcar_en_transito",
        "marcar_en_aduana",
        "marcar_despachado",
        "marcar_recibido",
        "verificar_alertas_despacho",
    ]

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<int:pk>/cambiar-estado/",
                self.admin_site.admin_view(self.view_cambiar_estado),
                name="importaciones_cambiar_estado",
            ),
            path(
                "<int:pk>/productos/",
                self.admin_site.admin_view(self.api_productos),
                name="importaciones_productos",
            ),
        ]
        return custom + urls

    def api_productos(self, request, pk):
        """Devuelve los productos de una OC en JSON para el desplegable."""
        importacion = get_object_or_404(Importacion, pk=pk)
        items = importacion.item_set.select_related("producto").all()
        data = []
        for item in items:
            data.append({
                "codigo": item.producto.codigo,
                "nombre": item.producto.nombre,
                "cantidad_ordenada": str(item.cantidad_ordenada),
                "cantidad_recibida": str(item.cantidad_recibida) if item.cantidad_recibida else "—",
                "precio": str(item.precio_unitario_usd) if item.precio_unitario_usd else "—",
                "unidad": item.producto.get_unidad_medida_display(),
            })
        return JsonResponse({"items": data, "numero_orden": importacion.numero_orden})

    @admin.display(description="Productos")
    def btn_productos(self, obj):
        count = obj.item_set.count()
        return format_html(
            '<button type="button" '
            'onclick="toggleProductos(event, {})" '
            'style="padding:3px 10px;background:#6c757d;color:white;border:none;'
            'border-radius:5px;font-size:12px;cursor:pointer;" '
            'title="Ver {} producto(s)">'
            '&#9660; {}</button>',
            obj.pk, count, count
        )

    def view_cambiar_estado(self, request, pk):
        importacion = get_object_or_404(Importacion, pk=pk)

        if request.method == "POST":
            estado_nuevo = request.POST.get("estado_nuevo", "").strip()
            notas = request.POST.get("notas", "").strip()
            estados_validos = [e[0] for e in Importacion.Estado.choices]

            if estado_nuevo not in estados_validos:
                messages.error(request, "Estado invalido.")
            elif estado_nuevo == importacion.estado:
                messages.warning(request, f"La importacion ya esta en estado '{importacion.get_estado_display()}'.")
            else:
                estado_anterior = importacion.estado
                importacion.estado = estado_nuevo
                importacion.save(update_fields=["estado", "actualizado_en"])
                CambioEstadoImportacion.objects.create(
                    importacion=importacion,
                    estado_anterior=estado_anterior,
                    estado_nuevo=estado_nuevo,
                    usuario=request.user,
                    notas=notas or f"Cambio de estado por {request.user.get_full_name() or request.user.username}",
                )
                importacion.verificar_alerta_despacho()
                messages.success(
                    request,
                    f"OC {importacion.numero_orden}: estado actualizado a '{importacion.get_estado_display()}'."
                )
            return redirect("admin:importaciones_importacion_changelist")

        ESTADOS_ORDEN = ["ORDENADO", "EN_TRANSITO", "EN_ADUANA", "DESPACHADO", "RECIBIDO", "CANCELADO"]
        idx = ESTADOS_ORDEN.index(importacion.estado) if importacion.estado in ESTADOS_ORDEN else -1
        estado_sugerido = ESTADOS_ORDEN[idx + 1] if idx >= 0 and idx < len(ESTADOS_ORDEN) - 1 else importacion.estado

        context = {
            **self.admin_site.each_context(request),
            "importacion": importacion,
            "estados": Importacion.Estado.choices,
            "estado_sugerido": estado_sugerido,
            "title": f"Cambiar estado - {importacion.numero_orden}",
            "opts": self.model._meta,
        }
        return TemplateResponse(request, "admin/importaciones/cambiar_estado.html", context)

    @admin.display(description="Estado", ordering="estado")
    def badge_estado(self, obj):
        colores = {
            "ORDENADO":    ("#3498db", "Ordenado"),
            "EN_TRANSITO": ("#9b59b6", "En transito"),
            "EN_ADUANA":   ("#e67e22", "En aduana"),
            "DESPACHADO":  ("#f1c40f", "Despachado"),
            "RECIBIDO":    ("#27ae60", "Recibido"),
            "CANCELADO":   ("#95a5a6", "Cancelado"),
        }
        color, label = colores.get(obj.estado, ("#999", obj.estado))
        return format_html(
            '<span style="color:white;background:{};padding:2px 8px;border-radius:4px;font-size:11px;">{}</span>',
            color, label,
        )

    @admin.display(description="ANMAT", ordering="requiere_anmat")
    def badge_requiere_anmat(self, obj):
        if obj.requiere_anmat:
            return mark_safe(
                '<span style="color:white;background:#e74c3c;padding:2px 8px;'
                'border-radius:10px;font-size:11px;font-weight:600;">Si</span>'
            )
        return mark_safe(
            '<span style="color:#7f8c8d;background:#ecf0f1;padding:2px 8px;'
            'border-radius:10px;font-size:11px;font-weight:600;">No</span>'
        )

    @admin.display(description="Despacho")
    def badge_despacho(self, obj):
        if obj.estado in ("RECIBIDO", "CANCELADO"):
            return "—"
        if obj.despacho:
            return mark_safe(
                '<span style="color:white;background:#27ae60;padding:2px 8px;'
                'border-radius:4px;font-size:11px;">Cargado</span>'
            )
        if obj.alerta_despacho_pendiente:
            return mark_safe(
                '<span style="color:white;background:#e74c3c;padding:2px 8px;'
                'border-radius:4px;font-size:11px;">Pendiente</span>'
            )
        return mark_safe(
            '<span style="color:#888;background:#f0f0f0;padding:2px 8px;'
            'border-radius:4px;font-size:11px;">Sin cargar</span>'
        )

    @admin.display(description="Accion")
    def btn_cambiar_estado(self, obj):
        if obj.estado in ("RECIBIDO", "CANCELADO"):
            return mark_safe('<span style="color:#aaa;font-size:12px;">Finalizada</span>')
        url = reverse("admin:importaciones_cambiar_estado", args=[obj.pk])
        return format_html(
            '<a href="{}" style="padding:4px 10px;background:#3498db;color:white;'
            'border-radius:5px;font-size:12px;font-weight:600;text-decoration:none;">'
            'Cambiar estado</a>',
            url,
        )

    def _cambiar_estado(self, request, queryset, estado_nuevo):
        for imp in queryset:
            estado_anterior = imp.estado
            imp.estado = estado_nuevo
            imp.save(update_fields=["estado", "actualizado_en"])
            CambioEstadoImportacion.objects.create(
                importacion=imp,
                estado_anterior=estado_anterior,
                estado_nuevo=estado_nuevo,
                usuario=request.user,
                notas="Cambio manual desde el panel de administracion",
            )
            imp.verificar_alerta_despacho()
        self.message_user(request, f"{queryset.count()} importacion(es) actualizada(s) a '{estado_nuevo}'.")

    @admin.action(description="Marcar como En transito")
    def marcar_en_transito(self, request, queryset):
        self._cambiar_estado(request, queryset, "EN_TRANSITO")

    @admin.action(description="Marcar como En aduana")
    def marcar_en_aduana(self, request, queryset):
        self._cambiar_estado(request, queryset, "EN_ADUANA")

    @admin.action(description="Marcar como Despachado")
    def marcar_despachado(self, request, queryset):
        self._cambiar_estado(request, queryset, "DESPACHADO")

    @admin.action(description="Marcar como Recibido")
    def marcar_recibido(self, request, queryset):
        self._cambiar_estado(request, queryset, "RECIBIDO")

    @admin.action(description="Verificar alertas de despacho pendiente")
    def verificar_alertas_despacho(self, request, queryset):
        for imp in queryset:
            imp.verificar_alerta_despacho()
        self.message_user(request, f"{queryset.count()} importacion(es) verificadas.")

    class Media:
        css = {}
        js = []

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["desplegable_js"] = True
        response = super().changelist_view(request, extra_context=extra_context)
        return response
