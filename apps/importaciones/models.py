from django.db import models
from django.conf import settings
from simple_history.models import HistoricalRecords
from apps.productos.models import Producto, Proveedor


class Importacion(models.Model):
    """
    Modulo principal - Gestion de Importaciones.
    Seguimiento completo de cada orden de compra internacional.
    """

    class Estado(models.TextChoices):
        ORDENADO    = "ORDENADO",    "Ordenado"
        EN_TRANSITO = "EN_TRANSITO", "En transito"
        EN_ADUANA   = "EN_ADUANA",   "En aduana"
        DESPACHADO  = "DESPACHADO",  "Despachado"
        RECIBIDO    = "RECIBIDO",    "Recibido"
        CANCELADO   = "CANCELADO",   "Cancelado"

    # Identificacion
    numero_orden = models.CharField(
        max_length=50,
        unique=True,
        help_text="Numero interno de orden de compra",
    )
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

    # Proforma
    numero_proforma = models.CharField(
        max_length=100,
        blank=True,
        help_text="Numero de proforma del proveedor",
    )
    proforma = models.FileField(
        upload_to="importaciones/proformas/",
        null=True,
        blank=True,
        help_text="Adjuntar proforma del proveedor (PDF, imagen, etc.)",
    )

    # Sector de destino
    sector_destino = models.ForeignKey(
        "productos.Sector",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="importaciones",
        help_text="Sector de la fabrica al que se destinan los productos de esta OC",
    )
    responsable_sector = models.CharField(
        max_length=200,
        blank=True,
        help_text="Nombre del responsable del sector que recibe los productos",
    )
    fecha_entrega_sector = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha estimada de entrega al sector",
    )
    notas_sector = models.TextField(
        blank=True,
        help_text="Notas adicionales sobre la entrega al sector",
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
        null=True, blank=True, help_text="Fecha real de ingreso al deposito"
    )

    # Tracking
    numero_tracking = models.CharField(max_length=200, blank=True)
    referencia_embarque = models.CharField(max_length=200, blank=True)

    # Guia de transporte / BL
    numero_bl = models.CharField(
        max_length=100,
        blank=True,
        help_text="Numero de BL o guia de transporte",
    )
    guia_transporte = models.FileField(
        upload_to="importaciones/guias/",
        null=True,
        blank=True,
        help_text="Adjuntar guia de transporte o Bill of Lading",
    )

    # Despacho aduanero
    numero_despacho = models.CharField(
        max_length=100,
        blank=True,
        help_text="Numero de despacho aduanero",
    )
    fecha_despacho = models.DateField(
        null=True,
        blank=True,
        help_text="Fecha real del despacho aduanero",
    )
    despacho = models.FileField(
        upload_to="importaciones/despachos/",
        null=True,
        blank=True,
        help_text="Adjuntar documentacion de despacho aduanero",
    )
    alerta_despacho_pendiente = models.BooleanField(
        default=False,
        help_text="True cuando paso la fecha ETA y aun no se cargo el despacho",
    )

    # Despachante
    despachante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="importaciones_despachadas",
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
        verbose_name = "Importacion"
        verbose_name_plural = "Importaciones"
        ordering = ["-fecha_orden"]

    def __str__(self):
        return f"OC {self.numero_orden} - {self.proveedor} ({self.get_estado_display()})"

    @property
    def requiere_anmat(self):
        return self.items.filter(requiere_anmat=True).exists()

    @property
    def despacho_pendiente(self):
        from django.utils import timezone
        if self.estado in ("RECIBIDO", "CANCELADO"):
            return False
        if self.fecha_eta and not self.despacho:
            return self.fecha_eta < timezone.now().date()
        return False

    def verificar_alerta_despacho(self):
        pendiente = self.despacho_pendiente
        if pendiente != self.alerta_despacho_pendiente:
            self.alerta_despacho_pendiente = pendiente
            self.save(update_fields=["alerta_despacho_pendiente"])

    def codigo_qr_data(self):
        return {
            "tipo": "importacion",
            "numero_orden": self.numero_orden,
            "id": self.pk,
        }


class ItemImportacion(models.Model):
    """Item dentro de una importacion con lotes asociados."""

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
        verbose_name = "Item de Importacion"
        verbose_name_plural = "Items de Importacion"
        unique_together = [["importacion", "producto"]]

    def __str__(self):
        return f"{self.producto.codigo} x{self.cantidad_ordenada} en OC {self.importacion.numero_orden}"


class LoteImportacion(models.Model):
    """
    Lote recibido asociado a un item de importacion.
    Los lotes nacen desde la OC — reemplaza al modulo de stock separado.
    """

    class Estado(models.TextChoices):
        BLOQUEADO = "BLOQUEADO", "Bloqueado - pendiente ANMAT"
        LIBERADO  = "LIBERADO",  "Liberado - disponible"
        AGOTADO   = "AGOTADO",   "Agotado"

    item = models.ForeignKey(
        ItemImportacion,
        on_delete=models.CASCADE,
        related_name="lotes",
    )
    numero_lote = models.CharField(max_length=100)
    cantidad_inicial = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad_actual = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(
        max_length=20, choices=Estado.choices, default=Estado.LIBERADO
    )
    fecha_ingreso = models.DateField()
    fecha_vencimiento = models.DateField(null=True, blank=True)
    certificado_calidad = models.FileField(
        upload_to="importaciones/lotes/certificados/",
        null=True,
        blank=True,
    )
    observaciones = models.TextField(blank=True)

    class Meta:
        verbose_name = "Lote de Importacion"
        verbose_name_plural = "Lotes de Importacion"
        ordering = ["-fecha_ingreso"]

    def __str__(self):
        return f"Lote {self.numero_lote} - {self.item.producto.codigo} ({self.estado})"

    def liberar(self):
        self.estado = self.Estado.LIBERADO
        self.save(update_fields=["estado"])


class CambioEstadoImportacion(models.Model):
    """Historial de cambios de estado de cada importacion."""

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
        verbose_name = "Cambio de Estado de Importacion"
        ordering = ["-fecha_hora"]

    def __str__(self):
        return (
            f"OC {self.importacion.numero_orden}: "
            f"{self.estado_anterior} -> {self.estado_nuevo}"
        )


class RequisitoCalidadImportacion(models.Model):
    """
    Documentos de requisitos de calidad asociados a una importacion.
    Fotos, planos, certificado de materia prima, CLV, carta compromiso, etc.
    """

    class TipoDocumento(models.TextChoices):
        FOTO             = "FOTO",    "Foto del producto"
        PLANO            = "PLANO",   "Plano tecnico"
        CERT_MP          = "CERT_MP", "Certificado de materia prima"
        CLV              = "CLV",     "CLV"
        CARTA_COMPROMISO = "CARTA",   "Carta compromiso"
        OTRO             = "OTRO",    "Otro"

    importacion = models.ForeignKey(
        Importacion,
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
        upload_to="importaciones/calidad/",
        help_text="Archivo del documento (PDF, imagen, etc.)",
    )
    fecha_carga = models.DateTimeField(auto_now_add=True)
    vigente = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Requisito de Calidad"
        verbose_name_plural = "Requisitos de Calidad"
        ordering = ["tipo", "-fecha_carga"]

    def __str__(self):
        return f"{self.get_tipo_display()} - OC {self.importacion.numero_orden}"
