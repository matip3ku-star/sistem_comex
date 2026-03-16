from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db.models import Sum
import json

from apps.productos.models import Producto
from apps.stock.models import Lote, MovimientoStock


def es_admin(user):
    return user.is_authenticated and (
        user.is_superuser or getattr(user, "rol", None) == "ADMIN"
    )


@staff_member_required
def vista_stock(request):
    categoria = request.GET.get("categoria", "TODOS")
    busqueda = request.GET.get("q", "").strip()

    productos_qs = Producto.objects.filter(activo=True).select_related("proveedor")

    if categoria != "TODOS":
        productos_qs = productos_qs.filter(categoria=categoria)

    if busqueda:
        from django.db.models import Q
        productos_qs = productos_qs.filter(
            Q(codigo__icontains=busqueda) |
            Q(nombre__icontains=busqueda) |
            Q(descripcion__icontains=busqueda) |
            Q(proveedor__nombre__icontains=busqueda)
        )

    productos_data = []
    for producto in productos_qs.order_by("categoria", "nombre"):
        lotes = Lote.objects.filter(
            producto=producto, estado__in=["LIBERADO", "BLOQUEADO"]
        )
        stock_disponible = lotes.filter(estado="LIBERADO").aggregate(
            total=Sum("cantidad_actual")
        )["total"] or 0
        stock_bloqueado = lotes.filter(estado="BLOQUEADO").aggregate(
            total=Sum("cantidad_actual")
        )["total"] or 0

        nivel = "normal"
        if producto.stock_minimo_seguridad > 0:
            if stock_disponible <= producto.stock_minimo_seguridad:
                nivel = "critico"
            elif producto.punto_reorden and stock_disponible <= producto.punto_reorden:
                nivel = "atencion"

        productos_data.append({
            "producto": producto,
            "stock_disponible": stock_disponible,
            "stock_bloqueado": stock_bloqueado,
            "stock_total": stock_disponible + stock_bloqueado,
            "nivel_alerta": nivel,
            "cantidad_lotes": lotes.count(),
        })

    context = {
        "title": "Control de Stock",
        "productos_data": productos_data,
        "categoria_actual": categoria,
        "busqueda": busqueda,
        "categorias": [
            ("TODOS", "Todos"),
            ("MP", "Materia Prima"),
            ("PI", "Productos Importados"),
            ("SU", "Suturas"),
            ("PT", "Producto Terminado"),
        ],
    }
    return render(request, "admin/stock/vista_stock.html", context)


@staff_member_required
def lotes_por_producto(request, producto_id):
    producto = get_object_or_404(Producto, pk=producto_id)
    lotes = Lote.objects.filter(
        producto=producto, estado__in=["LIBERADO", "BLOQUEADO"]
    ).order_by("-fecha_ingreso")

    data = []
    for lote in lotes:
        data.append({
            "id": lote.pk,
            "numero_lote": lote.numero_lote,
            "cantidad_actual": float(lote.cantidad_actual),
            "estado": lote.estado,
            "estado_display": lote.get_estado_display(),
            "fecha_ingreso": lote.fecha_ingreso.strftime("%d/%m/%Y"),
            "fecha_vencimiento": (
                lote.fecha_vencimiento.strftime("%d/%m/%Y")
                if lote.fecha_vencimiento
                else None
            ),
            "esta_vencido": lote.esta_vencido,
        })

    return JsonResponse({"lotes": data, "producto": producto.nombre})


@staff_member_required
@require_POST
def ajustar_stock_lote(request, lote_id):
    lote = get_object_or_404(Lote, pk=lote_id)

    try:
        body = json.loads(request.body)
        cantidad_nueva = float(body.get("cantidad_nueva"))
        motivo = body.get("motivo", "").strip() or "Ajuste manual"
    except (ValueError, KeyError, json.JSONDecodeError):
        return JsonResponse({"error": "Datos invalidos"}, status=400)

    if cantidad_nueva < 0:
        return JsonResponse({"error": "La cantidad no puede ser negativa"}, status=400)

    cantidad_anterior = float(lote.cantidad_actual)
    diferencia = cantidad_nueva - cantidad_anterior

    if diferencia == 0:
        return JsonResponse({"ok": True, "cantidad_nueva": cantidad_nueva})

    tipo = (
        MovimientoStock.TipoMovimiento.AJUSTE_POSITIVO
        if diferencia > 0
        else MovimientoStock.TipoMovimiento.AJUSTE_NEGATIVO
    )

    MovimientoStock.objects.create(
        lote=lote,
        tipo=tipo,
        cantidad=abs(diferencia),
        notas=f"{motivo} | {cantidad_anterior} -> {cantidad_nueva}",
        usuario=request.user,
        registrado_via_qr=False,
    )

    return JsonResponse({"ok": True, "cantidad_nueva": cantidad_nueva})


# ── AUDITORÍA — Solo administradores ─────────────────────────────────────────

@user_passes_test(es_admin, login_url="/admin/login/")
def log_auditoria(request):
    from django.contrib.auth import get_user_model
    Usuario = get_user_model()

    usuario_filtro = request.GET.get("usuario", "")
    tipo_filtro = request.GET.get("tipo", "")
    producto_filtro = request.GET.get("producto", "")

    movimientos = MovimientoStock.objects.select_related(
        "lote__producto", "usuario"
    ).order_by("-fecha_hora")

    if usuario_filtro:
        movimientos = movimientos.filter(usuario__id=usuario_filtro)
    if tipo_filtro:
        movimientos = movimientos.filter(tipo=tipo_filtro)
    if producto_filtro:
        movimientos = movimientos.filter(
            lote__producto__nombre__icontains=producto_filtro
        )

    movimientos = movimientos[:500]

    # Usuarios que tienen al menos un movimiento registrado
    usuarios = Usuario.objects.filter(
        movimientos_stock__isnull=False
    ).distinct().order_by("username")

    context = {
        "title": "Auditoria de Stock",
        "movimientos": movimientos,
        "tipos": MovimientoStock.TipoMovimiento.choices,
        "usuarios": usuarios,
        "usuario_filtro": usuario_filtro,
        "tipo_filtro": tipo_filtro,
        "producto_filtro": producto_filtro,
    }
    return render(request, "admin/stock/log_auditoria.html", context)
