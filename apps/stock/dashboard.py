from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta


@staff_member_required
def dashboard(request):
    from apps.productos.models import Producto
    from apps.stock.models import Lote
    from apps.importaciones.models import Importacion, ItemImportacion
    from apps.proveedores.models import Pago
    from apps.anmat.models import TramiteANMAT
    from apps.eventos.models import AlertaProveedor

    hoy = timezone.now().date()

    # ── KPIs globales ─────────────────────────────────────────────────────────
    normales = atencion = criticos = 0
    productos_criticos = []
    productos_atencion = []

    for producto in Producto.objects.filter(activo=True).select_related("proveedor"):
        stock = float(
            Lote.objects.filter(producto=producto, estado="LIBERADO")
            .aggregate(t=Sum("cantidad_actual"))["t"] or 0
        )
        minimo = float(producto.stock_minimo_seguridad)
        reorden = float(producto.punto_reorden or 0)

        if minimo > 0 and stock <= minimo:
            criticos += 1
            productos_criticos.append({
                "producto": producto, "stock": stock, "minimo": minimo,
            })
        elif reorden > 0 and stock <= reorden:
            atencion += 1
            productos_atencion.append({
                "producto": producto, "stock": stock, "reorden": reorden,
            })
        else:
            normales += 1

    productos_criticos = sorted(productos_criticos, key=lambda x: x["stock"])[:6]
    productos_atencion = sorted(productos_atencion, key=lambda x: x["stock"])[:6]

    # Lotes por vencer en 30 dias
    lotes_por_vencer = Lote.objects.filter(
        estado="LIBERADO",
        fecha_vencimiento__lte=hoy + timedelta(days=30),
        fecha_vencimiento__gte=hoy,
    ).select_related("producto").order_by("fecha_vencimiento")[:6]

    # ── Importaciones ─────────────────────────────────────────────────────────
    importaciones_qs = Importacion.objects.exclude(
        estado__in=["RECIBIDO", "CANCELADO"]
    ).select_related("proveedor").order_by("-fecha_orden")

    estados_count = {}
    for imp in importaciones_qs:
        estados_count[imp.estado] = estados_count.get(imp.estado, 0) + 1

    # Enriquecer cada importacion con datos calculados
    importaciones_activas = []
    for imp in importaciones_qs[:10]:
        dias_desde_orden = (hoy - imp.fecha_orden).days if imp.fecha_orden else None
        dias_hasta_eta = (imp.fecha_eta - hoy).days if imp.fecha_eta else None
        monto_total = None  # Se calcula en template si se necesita
        # Tramite ANMAT vinculado
        try:
            tramite_estado = imp.tramite_anmat.get_estado_display()
            tramite_urgente = imp.tramite_anmat.requiere_alerta_urgente
        except Exception:
            tramite_estado = None
            tramite_urgente = False
        importaciones_activas.append({
            "imp": imp,
            "dias_desde_orden": dias_desde_orden,
            "dias_hasta_eta": dias_hasta_eta,
            "tramite_estado": tramite_estado,
            "tramite_urgente": tramite_urgente,
        })

    proximas_llegadas = importaciones_qs.filter(
        fecha_eta__isnull=False
    ).order_by("fecha_eta")[:6]

    # ── Pagos ─────────────────────────────────────────────────────────────────
    pagos_pendientes = Pago.objects.filter(
        estado="PENDIENTE"
    ).select_related("proveedor", "importacion").order_by("fecha_vencimiento")[:10]

    pagos_vencidos_count = Pago.objects.filter(
        estado="PENDIENTE", fecha_vencimiento__lt=hoy
    ).count()

    pagos_hoy = Pago.objects.filter(
        estado="PENDIENTE", fecha_vencimiento=hoy
    ).count()

    total_pendiente_usd = Pago.objects.filter(
        estado="PENDIENTE", moneda="USD"
    ).aggregate(t=Sum("monto"))["t"] or 0

    # ── ANMAT ────────────────────────────────────────────────────────────────
    tramites_activos = TramiteANMAT.objects.exclude(
        estado__in=["FINALIZADO", "RECHAZADO"]
    ).select_related("importacion__proveedor").order_by("-fecha_presentacion")

    tramites_urgentes_count = tramites_activos.filter(
        estado__in=["OBSERVADO", "PAGO_VEP"]
    ).count()

    # ── Proveedores / Alertas ─────────────────────────────────────────────────
    alertas_activas = AlertaProveedor.objects.filter(
        resuelta=False
    ).select_related("proveedor").order_by("-creado_en")

    # ── Barra de alertas criticas ─────────────────────────────────────────────
    alertas_criticas = []
    if pagos_vencidos_count > 0:
        alertas_criticas.append({
            "tipo": "rojo",
            "msg": f"{pagos_vencidos_count} pago(s) vencido(s) sin registrar",
        })
    if pagos_hoy > 0:
        alertas_criticas.append({
            "tipo": "rojo",
            "msg": f"{pagos_hoy} pago(s) vence(n) HOY",
        })
    if tramites_urgentes_count > 0:
        alertas_criticas.append({
            "tipo": "naranja",
            "msg": f"{tramites_urgentes_count} tramite(s) ANMAT urgente(s)",
        })
    if criticos > 0:
        alertas_criticas.append({
            "tipo": "naranja",
            "msg": f"{criticos} producto(s) con stock critico",
        })
    for alerta in alertas_activas[:2]:
        alertas_criticas.append({
            "tipo": "naranja",
            "msg": f"Proveedor {alerta.proveedor.nombre}: {alerta.get_tipo_evento_display()}",
        })

    context = {
        "title": "Dashboard COMEX",
        "hoy": hoy,
        # KPIs
        "normales": normales,
        "atencion": atencion,
        "criticos": criticos,
        "total_importaciones_activas": importaciones_qs.count(),
        "alertas_proveedores_count": alertas_activas.count(),
        # Stock
        "productos_criticos": productos_criticos,
        "productos_atencion": productos_atencion,
        "lotes_por_vencer": lotes_por_vencer,
        # Importaciones
        "importaciones_activas": importaciones_activas,
        "estados_count": estados_count,
        "proximas_llegadas": proximas_llegadas,
        # Pagos
        "pagos_pendientes": pagos_pendientes,
        "pagos_vencidos_count": pagos_vencidos_count,
        "pagos_hoy": pagos_hoy,
        "total_pendiente_usd": total_pendiente_usd,
        # ANMAT
        "tramites_activos": tramites_activos[:8],
        "tramites_urgentes_count": tramites_urgentes_count,
        # Proveedores
        "alertas_activas": alertas_activas,
        # Alertas criticas
        "alertas_criticas": alertas_criticas,
    }
    return render(request, "admin/dashboard/dashboard.html", context)
