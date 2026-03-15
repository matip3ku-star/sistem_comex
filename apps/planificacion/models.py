# Módulo 6 - Planificación de Compras (COMEX)
# Los cálculos del punto de reorden se realizan en Producto.punto_reorden
# Este módulo extiende con proyecciones y el dashboard COMEX

from django.db import models
from apps.productos.models import Producto


class ProyeccionAgotamiento(models.Model):
    """
    Proyección automática de cuándo se agotará el stock de cada producto.
    Se recalcula diariamente vía tarea Celery.
    """

    producto = models.OneToOneField(
        Producto, on_delete=models.CASCADE, related_name="proyeccion"
    )
    dias_restantes = models.IntegerField(
        null=True, blank=True,
        help_text="Días hasta agotamiento estimado con consumo promedio actual",
    )
    fecha_agotamiento_estimada = models.DateField(null=True, blank=True)
    fecha_calculo = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Proyección de Agotamiento"
        verbose_name_plural = "Proyecciones de Agotamiento"

    def __str__(self):
        return f"Proyección {self.producto.codigo}: {self.dias_restantes} días"
