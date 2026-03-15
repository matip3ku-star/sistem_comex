from django.db import models
from django.conf import settings


class EventoExtraordinario(models.Model):
    """
    Módulo 7 - Eventos Extraordinarios.
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

    # Vinculado a una orden de importacion
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

    # Patron detectado
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
            f"{self.get_tipo_display()} — OC {self.importacion.numero_orden} "
            f"({self.importacion.proveedor.nombre}) — {self.fecha_evento}"
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
        Si se detecta, genera una alerta para revisar tiempos de reposicion.
        """
        from datetime import timedelta
        from django.utils import timezone

        if self.alerta_patron_generada:
            return

        periodo = timezone.now().date() - timedelta(days=180)

        # Buscar eventos del mismo tipo con el mismo proveedor
        count = EventoExtraordinario.objects.filter(
            importacion__proveedor=self.importacion.proveedor,
            tipo=self.tipo,
            fecha_evento__gte=periodo,
        ).count()

        if count >= self.LIMITE_PATRON:
            EventoExtraordinario.objects.filter(pk=self.pk).update(
                alerta_patron_generada=True
            )
            # Crear alerta en el sistema
            AlertaProveedor.objects.get_or_create(
                proveedor=self.importacion.proveedor,
                tipo_evento=self.tipo,
                resuelta=False,
                defaults={
                    "cantidad_eventos": count,
                    "mensaje": (
                        f"El proveedor {self.importacion.proveedor.nombre} registra "
                        f"{count} eventos de tipo '{self.get_tipo_display()}' "
                        f"en los ultimos 180 dias. Se recomienda revisar los tiempos "
                        f"de reposicion y solicitar material con mayor anticipacion."
                    ),
                }
            )


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
    cantidad_eventos = models.PositiveIntegerField()
    mensaje = models.TextField()
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
            f"Alerta {estado} — {self.proveedor.nombre} — "
            f"{self.get_tipo_evento_display()}"
        )

    def resolver(self, usuario, notas=""):
        from django.utils import timezone
        self.resuelta = True
        self.resuelta_en = timezone.now()
        self.resuelta_por = usuario
        self.notas_resolucion = notas
        self.save()
