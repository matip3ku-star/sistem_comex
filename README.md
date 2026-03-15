# Sistema COMEX - Mecanizados Gabriel S.A.

Sistema de gestión de compras en el exterior y provisión de materiales.

## Tecnología

- **Backend**: Django 5 + Django REST Framework
- **Base de datos**: PostgreSQL
- **Tareas asíncronas**: Celery + Redis
- **Alertas**: Telegram Bot

## Estructura de apps

| App | Módulo | Descripción |
|-----|--------|-------------|
| `usuarios` | — | Modelo de usuario con roles (COMEX, Depósito, Admin, Dirección) |
| `productos` | Módulo 1 | Maestro de productos e insumos |
| `stock` | Módulo 2 | Control de stock en depósito, lotes, movimientos |
| `importaciones` | Módulo 3 | Órdenes de compra internacionales |
| `anmat` | Módulo 4 | Trámites 14 puntos ANMAT |
| `materia_prima` | Módulo 5 | Trazabilidad de insumos de fabricación |
| `planificacion` | Módulo 6 | Proyecciones y punto de reorden |
| `eventos` | Módulo 7 | Eventos extraordinarios y detección de patrones |
| `proveedores` | Módulo 8 | Fichas, comunicaciones y pagos a proveedores |

## Instalación

### 1. Requisitos previos

- Python 3.11+
- PostgreSQL 15+
- Redis (para Celery)

### 2. Clonar y crear entorno virtual

```bash
git clone <repo>
cd comex_system
python -m venv venv
source venv/bin/activate        # Linux/Mac
# o
venv\Scripts\activate           # Windows
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env con los datos reales de PostgreSQL
```

### 5. Crear la base de datos

```bash
# En PostgreSQL:
createdb comex_db
```

### 6. Aplicar migraciones

```bash
python manage.py makemigrations
python manage.py migrate
```

### 7. Crear superusuario

```bash
python manage.py createsuperuser
```

### 8. Levantar el servidor

```bash
python manage.py runserver
```

### 9. (Opcional) Levantar Celery para alertas asíncronas

```bash
celery -A comex_system worker -l info
celery -A comex_system beat -l info
```

## Roles del sistema

| Rol | Acceso |
|-----|--------|
| `DEPOSITO` | Stock, movimientos, lotes, materia prima, eventos |
| `COMEX` | Importaciones, ANMAT, planificación, proveedores, pagos |
| `ADMIN` | Todo el sistema + configuración |
| `DIRECCION` | Lectura de planificación y pagos |

## Próximos pasos de desarrollo

1. `admin.py` para cada app (panel de administración)
2. `serializers.py` + `views.py` para la API REST
3. Sistema de alertas Telegram (Celery tasks)
4. Generación de códigos QR por producto/lote
5. Dashboard con proyecciones (Módulo 6)
6. Frontend (React / Vue / templates Django)
