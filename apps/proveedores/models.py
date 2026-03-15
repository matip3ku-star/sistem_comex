from django.db import models
from django.conf import settings
from django.utils import timezone
from simple_history.models import HistoricalRecords
from apps.productos.models import Proveedor


class FichaProveedor(models.Model):
    """
    Módulo 8.1 - Ficha completa del proveedor del exterior.
    Extiende el Proveedor básico con datos comerciales y de contacto.
    """

    class CanalComunicacion(models.TextChoices):
        EMAIL = "EMAIL", "Email"
        WHATSAPP = "WHATSAPP", "WhatsApp"
        AMBOS = "AMBOS", "Email y WhatsApp"

    class Moneda(models.TextChoices):
        USD = "USD", "Dólar estadounidense"
        EUR = "EUR", "Euro"
        CNY = "CNY", "Yuan chino"
        BRL = "BRL", "Real brasileño"

    proveedor = models.OneToOneField(
        Proveedor, on_delete=models.CASCADE, related_name="ficha"
    )

    # Contacto
    contacto_nombre = models.CharField(max_length=200, blank=True)
    contacto_email = models.EmailField(blank=True)
    contacto_whatsapp = models.CharField(max_length=30, blank=True)
    canal_habitual = models.CharField(
        max_length=10,
        choices=CanalComunicacion.choices,
        default=CanalComunicacion.EMAIL,
    )

    # Condiciones comerciales
    moneda_habitual = models.CharField(
        max_length=5, choices=Moneda.choices, default=Moneda.USD
    )
    plazo_pago_dias = models.PositiveIntegerField(
        default=0,
        help_text="Días de plazo para pago desde la factura",
    )
    modalidad_pago = models.CharField(
        max_length=200,
        blank=True,
        help_text="Transferencia bancaria / Pago anticipado / Cuenta corriente",
    )

    notas = models.TextField(blank=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Ficha de Proveedor"
        verbose_name_plural = "Fichas de Proveedores"

    def __str__(self):
        return f"Ficha: {self.proveedor.nombre}"


class Comunicacion(models.Model):
    """
    Módulo 8.2 - Registro de comunicaciones con proveedores.
    """

    class TipoComunicacion(models.TextChoices):
        COTIZACION = "COTIZACION", "Solicitud de cotización"
        CONFIRMACION_OC = "CONFIRMACION", "Confirmación de orden de compra"
        SEGUIMIENTO = "SEGUIMIENTO", "Seguimiento de embarque"
        RECLAMO = "RECLAMO", "Reclamo / Incidencia"
        OTRO = "OTRO", "Otro"

    class Canal(models.TextChoices):
        EMAIL = "EMAIL", "Email"
        WHATSAPP = "WHATSAPP", "WhatsApp"
        LLAMADA = "LLAMADA", "Llamada telefónica"
        OTRO = "OTRO", "Otro"

    proveedor = models.ForeignKey(
        Proveedor, on_delete=models.PROTECT, related_name="comunicaciones"
    )
    importacion = models.ForeignKey(
        "importaciones.Importacion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="comunicaciones",
    )
    tipo = models.CharField(max_length=20, choices=TipoComunicacion.choices)
    canal = models.CharField(max_length=10, choices=Canal.choices)
    resumen = models.TextField(help_text="Resumen del contenido de la comunicación")
    adjunto = models.FileField(upload_to="comunicaciones/", null=True, blank=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="comunicaciones",
    )
    fecha_hora = models.DateTimeField(default=timezone.now)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Comunicación"
        verbose_name_plural = "Comunicaciones"
        ordering = ["-fecha_hora"]

    def __str__(self):
        return (
            f"{self.get_tipo_display()} - {self.proveedor.nombre} "
            f"({self.fecha_hora:%d/%m/%Y})"
        )


class Pago(models.Model):
    """
    Módulo 8.3 - Gestión de pagos a proveedores del exterior.
    Control de vencimientos con alertas 7 días y 2 días antes.
    """

    class Modalidad(models.TextChoices):
        TRANSFERENCIA = "TRANSFERENCIA", "Transferencia bancaria internacional"
        ANTICIPO = "ANTICIPO", "Pago anticipado"
        CUENTA_CORRIENTE = "CTA_CTE", "Cuenta corriente"

    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        PAGADO = "PAGADO", "Pagado"
        VENCIDO = "VENCIDO", "Vencido"

    proveedor = models.ForeignKey(
        Proveedor, on_delete=models.PROTECT, related_name="pagos"
    )
    importacion = models.ForeignKey(
        "importaciones.Importacion",
        on_delete=models.PROTECT,
        related_name="pagos",
        null=True,
        blank=True,
    )
    modalidad = models.CharField(max_length=20, choices=Modalidad.choices)
    monto = models.DecimalField(max_digits=12, decimal_places=2)
    moneda = models.CharField(max_length=5, default="USD")
    tipo_cambio = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Tipo de cambio al momento de realizar la transferencia",
    )
    fecha_vencimiento = models.DateField(
        help_text="Fecha límite para realizar el pago sin penalidades"
    )
    estado = models.CharField(
        max_length=15, choices=Estado.choices, default=Estado.PENDIENTE
    )
    fecha_pago = models.DateField(null=True, blank=True)
    comprobante = models.FileField(
        upload_to="pagos/comprobantes/",
        null=True,
        blank=True,
        help_text="Comprobante bancario o confirmación de transferencia",
    )
    notas = models.TextField(blank=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="pagos_creados",
    )
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Pago"
        verbose_name_plural = "Pagos"
        ordering = ["fecha_vencimiento"]

    def __str__(self):
        return (
            f"Pago {self.moneda} {self.monto} a {self.proveedor.nombre} "
            f"vence {self.fecha_vencimiento} ({self.get_estado_display()})"
        )

    @property
    def dias_para_vencimiento(self):
        if self.estado != self.Estado.PENDIENTE:
            return None
        if not self.fecha_vencimiento:
            return None
        return (self.fecha_vencimiento - timezone.now().date()).days

    @property
    def nivel_urgencia(self):
        """
        - 'critico': vencido o vence hoy
        - 'urgente': vence en 2 días o menos
        - 'proximo': vence en 7 días o menos
        - 'normal': más de 7 días
        - None: ya pagado
        """
        dias = self.dias_para_vencimiento
        if dias is None:
            return None
        if dias <= 0:
            return "critico"
        if dias <= 2:
            return "urgente"
        if dias <= 7:
            return "proximo"
        return "normal"

    def registrar_pago(self, fecha_pago, tipo_cambio=None, comprobante=None, usuario=None):
        """Registra el pago y cambia el estado a PAGADO."""
        self.estado = self.Estado.PAGADO
        self.fecha_pago = fecha_pago
        if tipo_cambio:
            self.tipo_cambio = tipo_cambio
        if comprobante:
            self.comprobante = comprobante
        self.save()
