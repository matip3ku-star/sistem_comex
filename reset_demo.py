"""
reset_demo.py - Limpia los datos de prueba del sistema COMEX
Protegido con contrasena para uso exclusivo del administrador.
Ejecutar: python reset_demo.py
"""

import os
import sys
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "comex_system.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

print("")
print("=====================================================")
print("  SISTEMA COMEX - Limpieza de datos de prueba")
print("  Mecanizados Gabriel S.A.")
print("=====================================================")
print("")
print("  ATENCION: Esta operacion eliminara TODOS los datos")
print("  de prueba cargados durante la demostracion.")
print("  El sistema quedara listo para datos reales.")
print("")

# Verificar contrasena
CONTRASENA_RESET = "MG2025reset"
intentos = 0

while intentos < 3:
    clave = input("  Ingresa la contrasena de reset: ")
    if clave == CONTRASENA_RESET:
        break
    intentos += 1
    restantes = 3 - intentos
    if restantes > 0:
        print(f"  Contrasena incorrecta. {restantes} intento(s) restante(s).")
    else:
        print("")
        print("  [BLOQUEADO] Demasiados intentos fallidos. Operacion cancelada.")
        print("")
        sys.exit(1)

print("")
confirmacion = input("  Confirmas que queres eliminar TODOS los datos? (escribi SI para confirmar): ")
if confirmacion.strip().upper() != "SI":
    print("")
    print("  Operacion cancelada.")
    print("")
    sys.exit(0)

print("")
print("  Limpiando datos...")

from django.contrib.auth import get_user_model
from apps.eventos.models import EventoExtraordinario, AlertaProveedor
from apps.proveedores.models import FichaProveedor, Comunicacion, Pago
from apps.anmat.models import TramiteANMAT, CambioEstadoANMAT
from apps.stock.models import Lote, MovimientoStock, StockConsolidado
from apps.importaciones.models import Importacion, ItemImportacion, CambioEstadoImportacion
from apps.planificacion.models import ProyeccionAgotamiento
from apps.productos.models import Producto, Proveedor

Usuario = get_user_model()

# Orden de borrado respetando foreign keys
pasos = [
    ("Eventos extraordinarios",     EventoExtraordinario),
    ("Alertas de proveedor",         AlertaProveedor),
    ("Comunicaciones",               Comunicacion),
    ("Pagos",                        Pago),
    ("Cambios de estado ANMAT",      CambioEstadoANMAT),
    ("Tramites ANMAT",               TramiteANMAT),
    ("Movimientos de stock",         MovimientoStock),
    ("Stock consolidado",            StockConsolidado),
    ("Lotes",                        Lote),
    ("Items de importacion",         ItemImportacion),
    ("Cambios de estado importacion",CambioEstadoImportacion),
    ("Importaciones",                Importacion),
    ("Proyecciones de agotamiento",  ProyeccionAgotamiento),
    ("Fichas de proveedor",          FichaProveedor),
    ("Productos",                    Producto),
    ("Proveedores",                  Proveedor),
]

for nombre, modelo in pasos:
    count = modelo.objects.count()
    modelo.objects.all().delete()
    print(f"  OK {nombre}: {count} registros eliminados")

# Eliminar usuarios de prueba pero mantener Admin
usuarios_prueba = ["comex01", "deposito01", "deposito02", "direccion01"]
eliminados = Usuario.objects.filter(username__in=usuarios_prueba).delete()
print(f"  OK Usuarios de prueba eliminados")

print("")
print("=====================================================")
print("  RESET COMPLETADO")
print("=====================================================")
print("")
print("  El sistema esta listo para datos reales.")
print("")
print("  Usuario administrador conservado:")
print("  -> Usuario:  Admin")
print("  -> Password: Admin123")
print("")
print("  Proximos pasos:")
print("  1. Ingresar proveedores reales")
print("  2. Ingresar productos reales")
print("  3. Crear usuarios para el equipo")
print("  4. Comenzar a registrar importaciones")
print("")
