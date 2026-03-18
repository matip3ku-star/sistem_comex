from django.db import models
from django.conf import settings
from simple_history.models import HistoricalRecords
from apps.importaciones.models import Importacion


class TramiteANMAT(models.Model):
    """
    Modulo 4 - Tramites ANMAT.
    Gestion del documento '14 puntos' por cada importacion de producto regulado.
    """

    class Estado(models.TextChoices):
        PRESENTADO        = "PRESENTADO", "Presentado"
        EN_TRAMITE        = "EN_TRAMITE", "En tramite"
        OBSERVADO         = "OBSERVADO",  "Observado"
        PAGO_VEP_FALTANTE = "PAGO_VEP",  "Pago de VEP faltante"
        FINALIZADO        = "FINALIZADO", "Finalizado - Aprobado"
        RECHAZADO         = "RECHAZADO",  "Rechazado"

    ESTADOS_BLOQUEANTES = [
        Estado.PRESENTADO,
        Estado.EN_TRAMITE,
        Estado.OBSERVADO,
        Estado.PAGO_VEP_FALTANTE,
    ]
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

    # Documentacion
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
    comprobante_vep = models.FileField(
        upload_to="anmat/comprobantes_vep/",
        null=True,
        blank=True,
        help_text="Adjuntar comprobante de pago del VEP (PDF, imagen, etc.)",
    )

    # Aprobacion
    fecha_finalizacion = models.DateField(null=True, blank=True)
    certificado_aprobacion = models.FileField(
        upload_to="anmat/certificados/", null=True, blank=True
    )

    # Despachante responsable
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
        verbose_name = "Tramite ANMAT"
        verbose_name_plural = "Tramites ANMAT"
        ordering = ["-fecha_presentacion"]

    def __str__(self):
        return f"ANMAT OC {self.importacion.numero_orden} - {self.get_estado_display()}"

    @property
    def stock_bloqueado(self):
        return self.estado in self.ESTADOS_BLOQUEANTES

    @property
    def requiere_alerta_urgente(self):
        return self.estado in self.ESTADOS_ALERTA_URGENTE

    def finalizar(self, fecha_finalizacion, usuario=None):
        from django.utils import timezone
        self.estado = self.Estado.FINALIZADO
        self.fecha_finalizacion = fecha_finalizacion or timezone.now().date()
        self.save(update_fields=["estado", "fecha_finalizacion", "actualizado_en"])

        # Liberar lotes bloqueados del modelo LoteImportacion
        for item in self.importacion.item_set.all():
            for lote in item.lotes.filter(estado="BLOQUEADO"):
                lote.liberar()

        CambioEstadoANMAT.objects.create(
            tramite=self,
            estado_nuevo=self.Estado.FINALIZADO,
            usuario=usuario,
            notas="Lotes liberados automaticamente",
        )


class CambioEstadoANMAT(models.Model):
    """Historial de cambios de estado del tramite ANMAT."""

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
            f"{self.estado_anterior} -> {self.estado_nuevo}"
        )
