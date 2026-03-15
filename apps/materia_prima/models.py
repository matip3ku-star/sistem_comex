from django.db import models
from django.conf import settings
from simple_history.models import HistoricalRecords
from apps.productos.models import Producto


class LoteMateriaPrima(models.Model):
    """
    Módulo 5 - Trazabilidad de Materia Prima.
    Control de lotes de insumos para fabricación (acero, titanio, UHMWPE, etc.)
    """

    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name="lotes_mp",
        limit_choices_to={"categoria": "MP"},
    )
    numero_lote = models.CharField(max_length=100)
    proveedor_lote = models.CharField(
        max_length=200,
        blank=True,
        help_text="Nombre del proveedor según el certificado del lote",
    )
    cantidad_inicial = models.DecimalField(max_digits=10, decimal_places=3)
    cantidad_actual = models.DecimalField(max_digits=10, decimal_places=3)

    # Documentación de calidad
    fecha_ingreso = models.DateField()
    certificado_calidad = models.FileField(
        upload_to="mp/certificados/", null=True, blank=True
    )
    numero_certificado = models.CharField(max_length=100, blank=True)

    activo = models.BooleanField(default=True)
    observaciones = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Lote de Materia Prima"
        verbose_name_plural = "Lotes de Materia Prima"
        ordering = ["-fecha_ingreso"]
        unique_together = [["producto", "numero_lote"]]

    def __str__(self):
        return f"MP Lote {self.numero_lote} - {self.producto.codigo} ({self.cantidad_actual} disponible)"


class ConsumoMateriaPrima(models.Model):
    """
    Registro de consumo de materia prima vinculado a una orden de producción.
    """

    lote = models.ForeignKey(
        LoteMateriaPrima, on_delete=models.PROTECT, related_name="consumos"
    )
    orden_produccion = models.CharField(
        max_length=100,
        help_text="Número de orden de producción interna",
    )
    cantidad_consumida = models.DecimalField(max_digits=10, decimal_places=3)
    fecha_consumo = models.DateField()
    notas = models.TextField(blank=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="consumos_mp",
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Consumo de Materia Prima"
        verbose_name_plural = "Consumos de Materia Prima"
        ordering = ["-fecha_consumo"]

    def __str__(self):
        return (
            f"OP {self.orden_produccion} - {self.lote.producto.codigo} "
            f"x{self.cantidad_consumida}"
        )

    def save(self, *args, **kwargs):
        """Descuenta la cantidad del lote al registrar el consumo."""
        super().save(*args, **kwargs)
        lote = self.lote
        lote.cantidad_actual = models.F("cantidad_actual") - self.cantidad_consumida
        lote.save(update_fields=["cantidad_actual"])
