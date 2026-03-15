from django.db import models
from simple_history.models import HistoricalRecords


class Proveedor(models.Model):
    """
    Proveedor de productos importados.
    Relacionado con el Módulo 8 (detalle completo allá).
    Aquí solo la referencia básica para el catálogo.
    """

    nombre = models.CharField(max_length=200)
    pais_origen = models.CharField(max_length=100)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.pais_origen})"


class Producto(models.Model):
    """
    Módulo 1 - Maestro de Productos.
    Repositorio central de todos los ítems gestionados por el sistema.
    """

    class Categoria(models.TextChoices):
        MATERIA_PRIMA = "MP", "Materia Prima"
        PRODUCTO_IMPORTADO = "PI", "Producto Importado"
        PRODUCTO_TERMINADO = "PT", "Producto Terminado"
        SUTURA = "SU", "Sutura"

    class UnidadMedida(models.TextChoices):
        UNIDAD = "UN", "Unidad"
        KILOGRAMO = "KG", "Kilogramo"
        METRO = "MT", "Metro"
        LITRO = "LT", "Litro"
        CAJA = "CJ", "Caja"
        BARRA = "BR", "Barra"
        BLOQUE = "BL", "Bloque"

    # Identificación
    codigo = models.CharField(
        max_length=50,
        unique=True,
        help_text="Código único interno del producto",
    )
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)

    # Clasificación
    categoria = models.CharField(max_length=2, choices=Categoria.choices)
    unidad_medida = models.CharField(
        max_length=2, choices=UnidadMedida.choices, default=UnidadMedida.UNIDAD
    )

    # Proveedor
    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.PROTECT,
        related_name="productos",
        null=True,
        blank=True,
    )

    # Regulatorio ANMAT
    requiere_anmat = models.BooleanField(
        default=False,
        help_text="Indica si el producto requiere habilitación ANMAT por importación",
    )
    numero_registro_anmat = models.CharField(
        max_length=100,
        blank=True,
        help_text="Número de registro ANMAT (si aplica)",
    )
    vencimiento_habilitacion_anmat = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha de vencimiento de la habilitación ANMAT",
    )

    # Parámetros de planificación
    stock_minimo_seguridad = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Stock mínimo de seguridad (colchón ante imprevistos)",
    )
    tiempo_transito_dias = models.PositiveIntegerField(
        default=0,
        help_text="Días estimados desde orden hasta llegada al depósito",
    )
    tiempo_tramite_anmat_dias = models.PositiveIntegerField(
        default=0,
        help_text="Días estimados del trámite ANMAT (si aplica)",
    )
    consumo_promedio_mensual = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Calculado automáticamente o definido manualmente al inicio",
    )
    consumo_manual = models.BooleanField(
        default=True,
        help_text="True = ingresado manualmente. False = calculado por el sistema",
    )

    # Control
    activo = models.BooleanField(default=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ["codigo"]

    def __str__(self):
        return f"[{self.codigo}] {self.nombre}"

    @property
    def tiempo_total_reposicion(self):
        """Tiempo total = tránsito + ANMAT (si aplica)."""
        return self.tiempo_transito_dias + self.tiempo_tramite_anmat_dias

    @property
    def punto_reorden(self):
        """
        Punto de reorden = stock_mínimo + (consumo_promedio × tiempo_total_reposición).
        Retorna None si no hay consumo promedio definido.
        """
        if self.consumo_promedio_mensual is None:
            return None
        consumo_diario = self.consumo_promedio_mensual / 30
        return self.stock_minimo_seguridad + (
            consumo_diario * self.tiempo_total_reposicion
        )

    def codigo_qr_data(self):
        """Datos para generar el código QR del producto."""
        return {
            "tipo": "producto",
            "codigo": self.codigo,
            "nombre": self.nombre,
            "id": self.pk,
        }
