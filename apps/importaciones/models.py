from django.db import models
from django.conf import settings
from simple_history.models import HistoricalRecords
from apps.productos.models import Producto, Proveedor


class Importacion(models.Model):
    """
    Módulo 3 - Gestión de Importaciones.
    Seguimiento completo de cada orden de compra internacional.
    """

    class Estado(models.TextChoices):
        ORDENADO = "ORDENADO", "Ordenado"
        EN_TRANSITO = "EN_TRANSITO", "En tránsito"
        EN_ADUANA = "EN_ADUANA", "En aduana"
        DESPACHADO = "DESPACHADO", "Despachado"
        RECIBIDO = "RECIBIDO", "Recibido"
        CANCELADO = "CANCELADO", "Cancelado"

    # Identificación
    numero_orden = models.CharField(
        max_length=50,
        unique=True,
        help_text="Número interno de orden de compra",
    )

    # Producto y proveedor
    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.PROTECT,
        related_name="importaciones",
    )
    items = models.ManyToManyField(
        Producto,
        through="ItemImportacion",
        related_name="importaciones",
    )

    # Estado
    estado = models.CharField(
        max_length=15, choices=Estado.choices, default=Estado.ORDENADO
    )

    # Fechas
    fecha_orden = models.DateField()
    fecha_embarque = models.DateField(null=True, blank=True)
    fecha_eta = models.DateField(
        null=True, blank=True, help_text="Estimated Time of Arrival"
    )
    fecha_recepcion = models.DateField(
        null=True, blank=True, help_text="Fecha real de ingreso al depósito"
    )

    # Tracking
    numero_tracking = models.CharField(max_length=200, blank=True)
    referencia_embarque = models.CharField(max_length=200, blank=True)

    # Despachante
    despachante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="importaciones_despachadas",
        help_text="Usuario despachante responsable del trámite aduanero",
    )

    # Financiero
    costo_estimado_usd = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    moneda = models.CharField(max_length=10, default="USD")

    notas = models.TextField(blank=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="importaciones_creadas",
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Importación"
        verbose_name_plural = "Importaciones"
        ordering = ["-fecha_orden"]

    def __str__(self):
        return f"OC {self.numero_orden} - {self.proveedor} ({self.get_estado_display()})"

    @property
    def requiere_anmat(self):
        """True si algún ítem de la importación requiere trámite ANMAT."""
        return self.items.filter(requiere_anmat=True).exists()

    def codigo_qr_data(self):
        return {
            "tipo": "importacion",
            "numero_orden": self.numero_orden,
            "id": self.pk,
        }


class ItemImportacion(models.Model):
    """Ítem dentro de una importación (producto + cantidad)."""

    importacion = models.ForeignKey(
        Importacion, on_delete=models.CASCADE, related_name="item_set"
    )
    producto = models.ForeignKey(
        Producto, on_delete=models.PROTECT, related_name="items_importacion"
    )
    cantidad_ordenada = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad_recibida = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    precio_unitario_usd = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True
    )

    class Meta:
        verbose_name = "Ítem de Importación"
        verbose_name_plural = "Ítems de Importación"
        unique_together = [["importacion", "producto"]]

    def __str__(self):
        return f"{self.producto.codigo} x{self.cantidad_ordenada} en OC {self.importacion.numero_orden}"


class CambioEstadoImportacion(models.Model):
    """
    Historial de cambios de estado de cada importación.
    Permite auditoría completa y notificaciones.
    """

    importacion = models.ForeignKey(
        Importacion, on_delete=models.CASCADE, related_name="cambios_estado"
    )
    estado_anterior = models.CharField(
        max_length=15, choices=Importacion.Estado.choices, blank=True
    )
    estado_nuevo = models.CharField(
        max_length=15, choices=Importacion.Estado.choices
    )
    notas = models.TextField(blank=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    fecha_hora = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cambio de Estado de Importación"
        ordering = ["-fecha_hora"]

    def __str__(self):
        return (
            f"OC {self.importacion.numero_orden}: "
            f"{self.estado_anterior} → {self.estado_nuevo}"
        )
