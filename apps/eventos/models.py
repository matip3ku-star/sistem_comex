from django.db import models
from django.conf import settings


class EventoExtraordinario(models.Model):
    """
    Modulo 7 - Eventos Extraordinarios.
    Registra problemas o incidencias vinculados a una orden de importacion.
    Si el mismo tipo de evento ocurre 2+ veces con el mismo proveedor
    en los ultimos 180 dias, se genera una alerta automatica.
    """

    class TipoEvento(models.TextChoices):
        DEMORA_EMBARQUE  = "DEMORA_EMB",  "Demora en embarque"
        DEMORA_ADUANA    = "DEMORA_ADU",  "Demora en aduana"
        DEMORA_ANMAT     = "DEMORA_ANM",  "Demora en tramite ANMAT"
        CALIDAD_LOTE     = "CALIDAD",     "Problema de calidad en el lote"
        ENTREGA_INCOMP   = "ENT_INCOMP",  "Entrega incompleta"
        CANCELACION      = "CANCELACION", "Cancelacion de orden"
        PROBLEMA_PAGO    = "PAGO",        "Problemas en pago"
        OTRO             = "OTRO",        "Otro"

    LIMITE_PATRON = 2

    importacion = models.ForeignKey(
        "importaciones.Importacion",
        on_delete=models.PROTECT,
        related_name="eventos",
        help_text="Numero de orden de importacion afectada",
    )

    tipo = models.CharField(max_length=20, choices=TipoEvento.choices)
    fecha_evento = models.DateField()
    descripcion = models.TextField(
        help_text="Descripcion detallada del evento ocurrido",
    )
    impacto_dias = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Dias de retraso o impacto estimado (si aplica)",
    )

    alerta_patron_generada = models.BooleanField(
        default=False,
        help_text="True si este evento disparo una alerta de patron con el proveedor",
    )
    parametro_ajustado = models.BooleanField(
        default=False,
        help_text="True si se ajustaron los tiempos de reposicion del proveedor",
    )
    notas_ajuste = models.TextField(
        blank=True,
        help_text="Descripcion del ajuste realizado en los parametros del proveedor",
    )

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="eventos_registrados",
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Evento Extraordinario"
        verbose_name_plural = "Eventos Extraordinarios"
        ordering = ["-fecha_evento"]

    def __str__(self):
        return (
            f"{self.get_tipo_display()} - OC {self.importacion.numero_orden} "
            f"({self.importacion.proveedor.nombre}) - {self.fecha_evento}"
        )

    @property
    def proveedor(self):
        return self.importacion.proveedor

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._verificar_patron()

    def _verificar_patron(self):
        """
        Verifica si el mismo tipo de evento se repitio LIMITE_PATRON veces
        con el mismo proveedor en los ultimos 180 dias.
        Si se detecta, genera una alerta con recomendaciones concretas.
        """
        from datetime import timedelta
        from django.utils import timezone
        from django.db.models import Avg, Sum

        if self.alerta_patron_generada:
            return

        periodo = timezone.now().date() - timedelta(days=180)
        proveedor = self.importacion.proveedor

        # Buscar eventos del mismo tipo con el mismo proveedor
        eventos_patron = EventoExtraordinario.objects.filter(
            importacion__proveedor=proveedor,
            tipo=self.tipo,
            fecha_evento__gte=periodo,
        )
        count = eventos_patron.count()

        if count >= self.LIMITE_PATRON:
            EventoExtraordinario.objects.filter(pk=self.pk).update(
                alerta_patron_generada=True
            )

            # Calcular impacto promedio en dias
            impacto_promedio = eventos_patron.filter(
                impacto_dias__isnull=False
            ).aggregate(avg=Avg("impacto_dias"))["avg"]

            impacto_total = eventos_patron.filter(
                impacto_dias__isnull=False
            ).aggregate(total=Sum("impacto_dias"))["total"] or 0

            # OCs afectadas
            ocs_afectadas = list(
                eventos_patron.values_list(
                    "importacion__numero_orden", flat=True
                ).distinct()
            )
            ocs_str = ", ".join(ocs_afectadas) if ocs_afectadas else "N/A"

            # Dias adicionales recomendados = impacto promedio + 20% margen
            dias_adicionales = 0
            if impacto_promedio:
                dias_adicionales = int(impacto_promedio * 1.2)

            # Obtener tiempo de transito actual del proveedor
            productos_proveedor = proveedor.productos.filter(activo=True).first()
            tiempo_transito_actual = productos_proveedor.tiempo_transito_dias if productos_proveedor else 0

            # Generar recomendaciones según el tipo de evento
            recomendaciones = _generar_recomendaciones(
                self.tipo,
                proveedor.nombre,
                count,
                impacto_promedio,
                dias_adicionales,
                tiempo_transito_actual,
                ocs_str,
                impacto_total,
            )

            AlertaProveedor.objects.get_or_create(
                proveedor=proveedor,
                tipo_evento=self.tipo,
                resuelta=False,
                defaults={
                    "cantidad_eventos": count,
                    "mensaje": recomendaciones,
                    "dias_adicionales_recomendados": dias_adicionales,
                }
            )


def _generar_recomendaciones(tipo, nombre_proveedor, count, impacto_promedio,
                              dias_adicionales, tiempo_transito_actual, ocs_str, impacto_total):
    """Genera un mensaje de alerta con recomendaciones concretas según el tipo de evento."""

    impacto_str = f"{impacto_promedio:.0f}" if impacto_promedio else "no registrado"
    tiempo_nuevo = tiempo_transito_actual + dias_adicionales

    base = (
        f"PATRON DETECTADO - {nombre_proveedor}\n"
        f"{'='*50}\n"
        f"Tipo de incidencia: {_label_tipo(tipo)}\n"
        f"Ocurrencias en los ultimos 180 dias: {count}\n"
        f"Ordenes afectadas: {ocs_str}\n"
        f"Impacto promedio por evento: {impacto_str} dias\n"
        f"Impacto total acumulado: {impacto_total} dias\n"
        f"\n"
    )

    if tipo == "DEMORA_EMB":
        recomendacion = (
            f"RECOMENDACIONES:\n"
            f"1. Anticipar la orden de compra {dias_adicionales} dias adicionales.\n"
            f"   Tiempo de transito actual: {tiempo_transito_actual} dias\n"
            f"   Tiempo de transito recomendado: {tiempo_nuevo} dias\n"
            f"2. Solicitar confirmacion de fecha de embarque por escrito al momento de la OC.\n"
            f"3. Requerir actualizacion de estado semanal una vez confirmado el embarque.\n"
            f"4. Incrementar el stock de seguridad del proveedor en un 15-20%%.\n"
            f"5. Evaluar proveedor alternativo para contingencias."
        )
    elif tipo == "DEMORA_ADU":
        recomendacion = (
            f"RECOMENDACIONES:\n"
            f"1. Verificar con el despachante que la documentacion aduanera este\n"
            f"   completa ANTES del embarque (certificado de origen, factura, packing list).\n"
            f"2. Anticipar la orden {dias_adicionales} dias adicionales.\n"
            f"   Tiempo de transito actual: {tiempo_transito_actual} dias\n"
            f"   Tiempo de transito recomendado: {tiempo_nuevo} dias\n"
            f"3. Solicitar al proveedor pre-validacion de documentos con el despachante.\n"
            f"4. Mantener stock de seguridad ampliado durante tramites aduaneros."
        )
    elif tipo == "DEMORA_ANM":
        recomendacion = (
            f"RECOMENDACIONES:\n"
            f"1. Iniciar el tramite ANMAT con mayor anticipacion.\n"
            f"   Agregar {dias_adicionales} dias al tiempo estimado de tramite ANMAT.\n"
            f"2. Verificar que la documentacion del producto (14 puntos) este\n"
            f"   actualizada antes de cada importacion.\n"
            f"3. Mantener stock bloqueado separado para cubrir el periodo de tramite.\n"
            f"4. Consultar con ANMAT sobre pre-aprobacion de documentacion."
        )
    elif tipo == "CALIDAD":
        recomendacion = (
            f"RECOMENDACIONES:\n"
            f"1. Solicitar al proveedor certificado de calidad por lote ANTES del embarque.\n"
            f"2. Implementar inspeccion de calidad al ingreso de cada lote.\n"
            f"3. Exigir al proveedor plan de accion correctiva por escrito.\n"
            f"4. Evaluar aumentar el stock de seguridad en un 25%% para cubrir\n"
            f"   posibles rechazos de lote.\n"
            f"5. Considerar cambio o diversificacion de proveedor si el problema persiste."
        )
    elif tipo == "ENT_INCOMP":
        recomendacion = (
            f"RECOMENDACIONES:\n"
            f"1. Exigir confirmacion de stock disponible antes de emitir cada OC.\n"
            f"2. Solicitar packing list detallado antes del embarque.\n"
            f"3. Incluir clausula de penalidad por entrega incompleta en el contrato.\n"
            f"4. Considerar dividir ordenes grandes en envios parciales confirmados.\n"
            f"5. Incrementar stock de seguridad un 20%% para cubrir faltantes."
        )
    elif tipo == "CANCELACION":
        recomendacion = (
            f"RECOMENDACIONES:\n"
            f"1. URGENTE: Evaluar confiabilidad del proveedor para ordenes criticas.\n"
            f"2. Identificar proveedor alternativo como respaldo inmediato.\n"
            f"3. Exigir confirmacion formal de cada OC con acuse de recibo.\n"
            f"4. Incrementar stock de seguridad al maximo posible.\n"
            f"5. Revisar contrato comercial e incluir penalidades por cancelacion."
        )
    elif tipo == "PAGO":
        recomendacion = (
            f"RECOMENDACIONES:\n"
            f"1. Revisar el proceso interno de autorizacion de pagos al exterior.\n"
            f"2. Anticipar la gestion de transferencias {dias_adicionales} dias antes del vencimiento.\n"
            f"3. Verificar datos bancarios del proveedor antes de cada transferencia.\n"
            f"4. Mantener comunicacion fluida con el proveedor sobre fechas de pago."
        )
    else:
        recomendacion = (
            f"RECOMENDACIONES:\n"
            f"1. Revisar el historial de incidencias con este proveedor.\n"
            f"2. Anticipar ordenes {dias_adicionales} dias adicionales como medida preventiva.\n"
            f"   Tiempo de transito actual: {tiempo_transito_actual} dias\n"
            f"   Tiempo de transito recomendado: {tiempo_nuevo} dias\n"
            f"3. Establecer comunicacion formal con el proveedor para identificar\n"
            f"   causas raiz y plan de mejora."
        )

    return base + recomendacion


def _label_tipo(tipo):
    labels = {
        "DEMORA_EMB":  "Demora en embarque",
        "DEMORA_ADU":  "Demora en aduana",
        "DEMORA_ANM":  "Demora en tramite ANMAT",
        "CALIDAD":     "Problema de calidad en el lote",
        "ENT_INCOMP":  "Entrega incompleta",
        "CANCELACION": "Cancelacion de orden",
        "PAGO":        "Problemas en pago",
        "OTRO":        "Otro",
    }
    return labels.get(tipo, tipo)


class AlertaProveedor(models.Model):
    """
    Alerta generada automaticamente cuando un proveedor acumula
    LIMITE_PATRON eventos del mismo tipo.
    Visible solo para COMEX y Admin.
    """

    proveedor = models.ForeignKey(
        "productos.Proveedor",
        on_delete=models.CASCADE,
        related_name="alertas",
    )
    tipo_evento = models.CharField(
        max_length=20,
        choices=EventoExtraordinario.TipoEvento.choices,
    )
    cantidad_eventos = models.PositiveIntegerField(default=0)
    mensaje = models.TextField()
    dias_adicionales_recomendados = models.PositiveIntegerField(
        default=0,
        help_text="Dias adicionales recomendados para anticipar la proxima orden",
    )
    resuelta = models.BooleanField(
        default=False,
        help_text="Marcar como resuelta cuando se ajusten los parametros",
    )
    notas_resolucion = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    resuelta_en = models.DateTimeField(null=True, blank=True)
    resuelta_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="alertas_resueltas",
    )

    class Meta:
        verbose_name = "Alerta de Proveedor"
        verbose_name_plural = "Alertas de Proveedores"
        ordering = ["-creado_en"]

    def __str__(self):
        estado = "Resuelta" if self.resuelta else "Pendiente"
        return (
            f"Alerta {estado} - {self.proveedor.nombre} - "
            f"{self.get_tipo_evento_display()}"
        )

    def resolver(self, usuario, notas=""):
        from django.utils import timezone
        self.resuelta = True
        self.resuelta_en = timezone.now()
        self.resuelta_por = usuario
        self.notas_resolucion = notas
        self.save()
