from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Importacion, CambioEstadoImportacion


def puede_cambiar_estado(user):
    """Solo COMEX y Admin pueden cambiar estado de importaciones."""
    return user.is_authenticated and (
        getattr(user, 'rol', None) in ('COMEX', 'ADMIN') or user.is_superuser
    )


@login_required
def lista_importaciones(request):
    """Lista de importaciones con filtros por estado."""
    estado_filtro = request.GET.get('estado', '')
    fecha_filtro = request.GET.get('fecha', '')
    importaciones = Importacion.objects.select_related('proveedor').prefetch_related('item_set__producto')

    if estado_filtro:
        importaciones = importaciones.filter(estado=estado_filtro)

    if fecha_filtro:
        try:
            from datetime import datetime
            fecha = datetime.strptime(fecha_filtro, '%Y-%m-%d').date()
            importaciones = importaciones.filter(fecha_orden=fecha)
        except ValueError:
            fecha_filtro = ''

    importaciones = importaciones.order_by('-fecha_orden')

    estados = Importacion.Estado.choices
    puede_editar = puede_cambiar_estado(request.user)

    context = {
        'importaciones': importaciones,
        'estados': estados,
        'estado_filtro': estado_filtro,
        'fecha_filtro': fecha_filtro,
        'puede_editar': puede_editar,
        'total': importaciones.count(),
    }
    return render(request, 'importaciones/lista.html', context)


@login_required
@require_POST
def cambiar_estado(request, pk):
    """Cambia el estado de una importación. Solo COMEX y Admin."""
    if not puede_cambiar_estado(request.user):
        messages.error(request, "No tenés permisos para cambiar el estado de importaciones.")
        return redirect('importaciones:lista')

    importacion = get_object_or_404(Importacion, pk=pk)
    estado_nuevo = request.POST.get('estado_nuevo', '').strip()
    notas = request.POST.get('notas', '').strip()

    estados_validos = [e[0] for e in Importacion.Estado.choices]
    if estado_nuevo not in estados_validos:
        messages.error(request, "Estado inválido.")
        return redirect('importaciones:lista')

    if estado_nuevo == importacion.estado:
        messages.warning(request, f"La importación {importacion.numero_orden} ya está en estado '{importacion.get_estado_display()}'.")
        return redirect('importaciones:lista')

    estado_anterior = importacion.estado
    importacion.estado = estado_nuevo
    importacion.save(update_fields=['estado', 'actualizado_en'])

    CambioEstadoImportacion.objects.create(
        importacion=importacion,
        estado_anterior=estado_anterior,
        estado_nuevo=estado_nuevo,
        usuario=request.user,
        notas=notas or f"Cambio de estado por {request.user.get_full_name() or request.user.username}",
    )

    messages.success(
        request,
        f"OC {importacion.numero_orden}: estado actualizado a '{importacion.get_estado_display()}'."
    )
    return redirect('importaciones:lista')
