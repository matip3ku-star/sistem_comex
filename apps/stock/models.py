from django.db import models
from django.conf import settings
from simple_history.models import HistoricalRecords
from apps.productos.models import Producto


class Lote(models.Model):
    """
    Lote de un producto en depósito.
    Cada ingreso genera un lote con trazabilidad independiente.
    """

    producto = models.ForeignKey(
        Producto, on_delete=models.PROTECT, related_name="lotes"
    )
    numero_lote = models.CharField(max_length=100)
    cantidad_inicial = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad_actual = models.DecimalField(max_digits=10, decimal_places=2)

    # Categoría del lote
    class Categoria(models.TextChoices):
        MATERIA_PRIMA  = "MP",  "Materia Prima"
        SEMIELABORADO  = "SE",  "Semielaborado"
        INSUMOS        = "IN",  "Insumos"
        MAQUINARIA     = "MA",  "Maquinaria"

    categoria = models.CharField(
        max_length=2,
        choices=Categoria.choices,
        default=Categoria.INSUMOS,
        help_text="Categoría del lote ingresado",
    )

    # Estado: stock bloqueado hasta aprobación ANMAT o libre para uso
    class Estado(models.TextChoices):
        BLOQUEADO = "BLOQUEADO", "Bloqueado - pendiente ANMAT"
        LIBERADO  = "LIBERADO",  "Liberado - disponible"
        AGOTADO   = "AGOTADO",   "Agotado"

    estado = models.CharField(
        max_length=20, choices=Estado.choices, default=Estado.LIBERADO
    )

    fecha_ingreso = models.DateField()
    fecha_vencimiento = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha de vencimiento o esterilización del lote",
    )
    certificado_calidad = models.FileField(
        upload_to="certificados/", null=True, blank=True
    )
    observaciones = models.TextField(blank=True)

    # Trazabilidad: de qué importación viene
    importacion = models.ForeignKey(
        "importaciones.Importacion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="lotes",
    )

    creado_en = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Lote"
        verbose_name_plural = "Lotes"
        ordering = ["-fecha_ingreso"]
        unique_together = [["producto", "numero_lote"]]

    def __str__(self):
        return f"Lote {self.numero_lote} - {self.producto.codigo} ({self.estado})"

    @property
    def esta_vencido(self):
        from django.utils import timezone
        if self.fecha_vencimiento:
            return self.fecha_vencimiento < timezone.now().date()
        return False

    def liberar(self):
        """Libera el lote cuando ANMAT aprueba el trámite."""
        self.estado = self.Estado.LIBERADO
        self.save(update_fields=["estado"])

    def codigo_qr_data(self):
        return {
            "tipo": "lote",
            "producto_codigo": self.producto.codigo,
            "numero_lote": self.numero_lote,
            "id": self.pk,
        }


class MovimientoStock(models.Model):
    """
    Registro de cada movimiento de stock (entrada o salida).
    Operación realizable desde celular con QR.
    """

    class TipoMovimiento(models.TextChoices):
        ENTRADA          = "ENTRADA",    "Entrada al depósito"
        SALIDA           = "SALIDA",     "Salida / Consumo"
        AJUSTE_POSITIVO  = "AJUSTE_POS", "Ajuste positivo"
        AJUSTE_NEGATIVO  = "AJUSTE_NEG", "Ajuste negativo"
        BAJA_VENCIMIENTO = "BAJA_VEN",   "Baja por vencimiento"
        BAJA_DANIO       = "BAJA_DAN",   "Baja por daño"

    class MotivoSalida(models.TextChoices):
        VENTA      = "VENTA",      "Venta / Entrega"
        PRODUCCION = "PRODUCCION", "Consumo en producción"
        DEVOLUCION = "DEVOLUCION", "Devolución a proveedor"
        BAJA       = "BAJA",       "Baja (vencimiento / daño)"
        OTRO       = "OTRO",       "Otro"

    lote = models.ForeignKey(
        Lote, on_delete=models.PROTECT, related_name="movimientos"
    )
    tipo = models.CharField(max_length=15, choices=TipoMovimiento.choices)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    motivo = models.CharField(
        max_length=20, choices=MotivoSalida.choices, blank=True
    )
    notas = models.TextField(blank=True)

    # Quién registró y cuándo
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="movimientos_stock",
    )
    fecha_hora = models.DateTimeField(auto_now_add=True)
    registrado_via_qr = models.BooleanField(
        default=False,
        help_text="True si fue registrado escaneando código QR desde celular",
    )

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Movimiento de Stock"
        verbose_name_plural = "Movimientos de Stock"
        ordering = ["-fecha_hora"]

    def __str__(self):
        return (
            f"{self.get_tipo_display()} - {self.lote} - {self.cantidad} "
            f"({self.fecha_hora:%d/%m/%Y %H:%M})"
        )

    def save(self, *args, **kwargs):
        """Actualiza la cantidad actual del lote al guardar el movimiento."""
        super().save(*args, **kwargs)
        lote = self.lote
        if self.tipo in [
            self.TipoMovimiento.ENTRADA,
            self.TipoMovimiento.AJUSTE_POSITIVO,
        ]:
            lote.cantidad_actual = models.F("cantidad_actual") + self.cantidad
        else:
            lote.cantidad_actual = models.F("cantidad_actual") - self.cantidad
        lote.save(update_fields=["cantidad_actual"])
        lote.refresh_from_db()
        if lote.cantidad_actual <= 0:
            lote.estado = Lote.Estado.AGOTADO
            lote.save(update_fields=["estado"])


class StockConsolidado(models.Model):
    """
    Vista consolidada del stock actual por producto.
    Se actualiza via señales cuando cambian los lotes.
    Facilita las consultas rápidas del dashboard.
    """

    producto = models.OneToOneField(
        Producto, on_delete=models.CASCADE, related_name="stock_consolidado"
    )
    stock_disponible = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Stock liberado y disponible para uso/venta",
    )
    stock_bloqueado = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text="Stock pendiente de aprobación ANMAT",
    )
    stock_total = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Stock Consolidado"
        verbose_name_plural = "Stocks Consolidados"

    def __str__(self):
        return f"Stock {self.producto.codigo}: {self.stock_disponible} disponible"

    @property
    def nivel_alerta(self):
        producto = self.producto
        if self.stock_disponible <= producto.stock_minimo_seguridad:
            return "critico"
        punto = producto.punto_reorden
        if punto and self.stock_disponible <= punto:
            return "atencion"
        return "normal"
