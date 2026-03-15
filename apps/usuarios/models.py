from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    """
    Modelo de usuario personalizado con roles del sistema COMEX.
    """

    class Rol(models.TextChoices):
        DEPOSITO = "DEPOSITO", "Encargado de Depósito"
        COMEX = "COMEX", "Encargado de COMEX"
        ADMINISTRADOR = "ADMIN", "Administrador"
        DIRECCION = "DIRECCION", "Dirección / Finanzas"

    rol = models.CharField(
        max_length=20,
        choices=Rol.choices,
        default=Rol.DEPOSITO,
    )
    telefono = models.CharField(max_length=20, blank=True)
    telegram_chat_id = models.CharField(
        max_length=50,
        blank=True,
        help_text="Chat ID de Telegram para recibir alertas automáticas",
    )

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_rol_display()})"

    @property
    def es_comex(self):
        return self.rol == self.Rol.COMEX

    @property
    def es_deposito(self):
        return self.rol == self.Rol.DEPOSITO

    @property
    def es_admin(self):
        return self.rol == self.Rol.ADMINISTRADOR

    @property
    def es_direccion(self):
        return self.rol == self.Rol.DIRECCION
