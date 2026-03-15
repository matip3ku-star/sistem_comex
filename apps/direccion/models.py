from django.db import models


class Dashboard(models.Model):
    """
    Modelo proxy sin tabla real.
    Solo existe para que Jazzmin muestre la app 'Direccion'
    en el menu lateral con el link al dashboard.
    """

    class Meta:
        managed = False
        verbose_name = "Dashboard"
        verbose_name_plural = "Dashboard COMEX"
        app_label = "direccion"
