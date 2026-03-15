from django.db import models
from django.conf import settings
from simple_history.models import HistoricalRecords
from apps.importaciones.models import Importacion


class TramiteANMAT(models.Model):
    """
    Módulo 4 - Trámites ANMAT.
    Gestión del documento '14 puntos' por cada importación de producto regulado.
    El stock NO se libera hasta que el estado sea FINALIZADO.
    """

    class Estado(models.TextChoices):
        PRESENTADO = "PRESENTADO", "Presentado"
        EN_TRAMITE = "EN_TRAMITE", "En trámite"
        OBSERVADO = "OBSERVADO", "Observado"
        PAGO_VEP_FALTANTE = "PAGO_VEP", "Pago de VEP faltante"
        FINALIZADO = "FINALIZADO", "Finalizado - Aprobado"
        RECHAZADO = "RECHAZADO", "Rechazado"

    # Estados que bloquean el stock
    ESTADOS_BLOQUEANTES = [
        Estado.PRESENTADO,
        Estado.EN_TRAMITE,
        Estado.OBSERVADO,
        Estado.PAGO_VEP_FALTANTE,
    ]
    # Estados que requieren alerta urgente
    ESTADOS_ALERTA_URGENTE = [
        Estado.OBSERVADO,
        Estado.PAGO_VEP_FALTANTE,
    ]

    importacion = models.OneToOneField(
        Importacion,
        on_delete=models.PROTECT,
        related_name="tramite_anmat",
    )
    estado = models.CharField(
        max_length=20, choices=Estado.choices, default=Estado.PRESENTADO
    )

    # Documentación
    fecha_presentacion = models.DateField()
    numero_expediente = models.CharField(max_length=100, blank=True)
    documento_14_puntos = models.FileField(
        upload_to="anmat/14_puntos/", null=True, blank=True
    )

    # Observaciones ANMAT
    observaciones_anmat = models.TextField(
        blank=True,
        help_text="Texto de las observaciones recibidas de ANMAT (si aplica)",
    )
    respuesta_observaciones = models.FileField(
        upload_to="anmat/respuestas/", null=True, blank=True
    )

    # VEP
    numero_vep = models.CharField(max_length=100, blank=True)
    monto_vep = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    fecha_pago_vep = models.DateField(null=True, blank=True)

    # Aprobación
    fecha_finalizacion = models.DateField(null=True, blank=True)
    certificado_aprobacion = models.FileField(
        upload_to="anmat/certificados/", null=True, blank=True
    )

    # Despachante responsable del trámite
    despachante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tramites_anmat",
    )

    notas = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Trámite ANMAT"
        verbose_name_plural = "Trámites ANMAT"
        ordering = ["-fecha_presentacion"]

    def __str__(self):
        return (
            f"ANMAT OC {self.importacion.numero_orden} - {self.get_estado_display()}"
        )

    @property
    def stock_bloqueado(self):
        return self.estado in self.ESTADOS_BLOQUEANTES

    @property
    def requiere_alerta_urgente(self):
        return self.estado in self.ESTADOS_ALERTA_URGENTE

    def finalizar(self, fecha_finalizacion, usuario=None):
        """
        Finaliza el trámite ANMAT y libera automáticamente el stock de la importación.
        """
        from django.utils import timezone

        self.estado = self.Estado.FINALIZADO
        self.fecha_finalizacion = fecha_finalizacion or timezone.now().date()
        self.save(update_fields=["estado", "fecha_finalizacion", "actualizado_en"])

        # Liberar todos los lotes asociados a la importación
        for lote in self.importacion.lotes.filter(estado="BLOQUEADO"):
            lote.liberar()

        # Registrar cambio
        CambioEstadoANMAT.objects.create(
            tramite=self,
            estado_nuevo=self.Estado.FINALIZADO,
            usuario=usuario,
            notas="Stock liberado automáticamente",
        )


class CambioEstadoANMAT(models.Model):
    """Historial de cambios de estado del trámite ANMAT."""

    tramite = models.ForeignKey(
        TramiteANMAT, on_delete=models.CASCADE, related_name="cambios_estado"
    )
    estado_anterior = models.CharField(
        max_length=20, choices=TramiteANMAT.Estado.choices, blank=True
    )
    estado_nuevo = models.CharField(
        max_length=20, choices=TramiteANMAT.Estado.choices
    )
    notas = models.TextField(blank=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    fecha_hora = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cambio de Estado ANMAT"
        ordering = ["-fecha_hora"]

    def __str__(self):
        return (
            f"ANMAT OC {self.tramite.importacion.numero_orden}: "
            f"{self.estado_anterior} → {self.estado_nuevo}"
        )
