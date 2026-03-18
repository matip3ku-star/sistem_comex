from django.db import models
from simple_history.models import HistoricalRecords


class Sector(models.Model):
    """
    Sector de destino dentro de la fabrica para cada producto importado.
    Editable desde el admin por el encargado.
    Ejemplos: Pulido, Deposito Esteril, Area Centros y Tornos, etc.
    """
    nombre = models.CharField(max_length=100, unique=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Sector"
        verbose_name_plural = "Sectores"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Proveedor(models.Model):
    """
    Proveedor de productos importados.
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
    Modulo 1 - Maestro de Productos.
    Repositorio central de todos los items gestionados por el sistema.
    """

    class Categoria(models.TextChoices):
        MATERIA_PRIMA       = "MP", "Materia Prima"
        PRODUCTO_IMPORTADO  = "PI", "Producto Importado"
        PRODUCTO_TERMINADO  = "PT", "Producto Terminado"
        SUTURA              = "SU", "Sutura"

    class UnidadMedida(models.TextChoices):
        UNIDAD      = "UN", "Unidad"
        KILOGRAMO   = "KG", "Kilogramo"
        METRO       = "MT", "Metro"
        LITRO       = "LT", "Litro"
        CAJA        = "CJ", "Caja"
        BARRA       = "BR", "Barra"
        BLOQUE      = "BL", "Bloque"

    # Identificacion
    codigo = models.CharField(
        max_length=50,
        unique=True,
        help_text="Codigo unico interno del producto",
    )
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)

    # Clasificacion
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
        help_text="Indica si el producto requiere habilitacion ANMAT por importacion",
    )
    numero_registro_anmat = models.CharField(
        max_length=100,
        blank=True,
        help_text="Numero de registro ANMAT (si aplica)",
    )
    vencimiento_habilitacion_anmat = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha de vencimiento de la habilitacion ANMAT",
    )

    # Parametros de planificacion
    stock_minimo_seguridad = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Stock minimo de seguridad",
    )
    tiempo_transito_dias = models.PositiveIntegerField(
        default=0,
        help_text="Dias estimados desde orden hasta llegada al deposito",
    )
    tiempo_tramite_anmat_dias = models.PositiveIntegerField(
        default=0,
        help_text="Dias estimados del tramite ANMAT (si aplica)",
    )
    consumo_promedio_mensual = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Calculado automaticamente o definido manualmente al inicio",
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
        return self.tiempo_transito_dias + self.tiempo_tramite_anmat_dias

    @property
    def punto_reorden(self):
        if self.consumo_promedio_mensual is None:
            return None
        consumo_diario = self.consumo_promedio_mensual / 30
        return self.stock_minimo_seguridad + (
            consumo_diario * self.tiempo_total_reposicion
        )

    def codigo_qr_data(self):
        return {
            "tipo": "producto",
            "codigo": self.codigo,
            "nombre": self.nombre,
            "id": self.pk,
        }


class RequisitoCalidad(models.Model):
    """
    Documentos de requerimientos de calidad asociados a un producto.
    Fotos, planos, certificado de materia prima, CLV, carta compromiso, etc.
    """

    class TipoDocumento(models.TextChoices):
        FOTO            = "FOTO",    "Foto del producto"
        PLANO           = "PLANO",   "Plano tecnico"
        CERT_MP         = "CERT_MP", "Certificado de materia prima"
        CLV             = "CLV",     "CLV"
        CARTA_COMPROMISO = "CARTA",  "Carta compromiso"
        OTRO            = "OTRO",    "Otro"

    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name="requisitos_calidad",
    )
    tipo = models.CharField(
        max_length=20,
        choices=TipoDocumento.choices,
        help_text="Tipo de documento de calidad",
    )
    descripcion = models.CharField(
        max_length=200,
        blank=True,
        help_text="Descripcion adicional del documento",
    )
    archivo = models.FileField(
        upload_to="productos/calidad/",
        help_text="Archivo del documento (PDF, imagen, etc.)",
    )
    fecha_carga = models.DateTimeField(auto_now_add=True)
    vigente = models.BooleanField(
        default=True,
        help_text="Desmarcar si el documento fue reemplazado por una version mas nueva",
    )

    class Meta:
        verbose_name = "Requisito de Calidad"
        verbose_name_plural = "Requisitos de Calidad"
        ordering = ["tipo", "-fecha_carga"]

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.producto.codigo}"
