from rest_framework import serializers
from .models import Producto, Proveedor


class ProveedorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proveedor
        fields = "__all__"


class ProductoSerializer(serializers.ModelSerializer):
    proveedor_nombre = serializers.CharField(source="proveedor.nombre", read_only=True)
    punto_reorden = serializers.FloatField(read_only=True)
    tiempo_total_reposicion = serializers.IntegerField(read_only=True)

    class Meta:
        model = Producto
        fields = "__all__"


class ProductoResumenSerializer(serializers.ModelSerializer):
    """Versión resumida para listas y selects."""
    class Meta:
        model = Producto
        fields = ("id", "codigo", "nombre", "categoria", "unidad_medida", "requiere_anmat")
