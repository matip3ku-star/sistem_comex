from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="cambia-esto-en-produccion")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

DJANGO_APPS = [
    "jazzmin",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "corsheaders",
    "simple_history",
]

LOCAL_APPS = [
    "apps.usuarios",
    "apps.productos",
    "apps.stock",
    "apps.importaciones",
    "apps.anmat",
    "apps.planificacion",
    "apps.eventos",
    "apps.proveedores",
    "apps.direccion",
    "apps.importador",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
]

ROOT_URLCONF = "comex_system.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "comex_system.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME", default="comex_db"),
        "USER": env("DB_USER", default="postgres"),
        "PASSWORD": env("DB_PASSWORD", default=""),
        "HOST": env("DB_HOST", default="localhost"),
        "PORT": env("DB_PORT", default="5432"),
    }
}

AUTH_USER_MODEL = "usuarios.Usuario"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-ar"
TIME_ZONE = "America/Argentina/Buenos_Aires"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
}

CELERY_BROKER_URL = env("REDIS_URL", default="")
CELERY_RESULT_BACKEND = env("REDIS_URL", default="")
CELERY_TIMEZONE = TIME_ZONE

TELEGRAM_BOT_TOKEN = env("TELEGRAM_BOT_TOKEN", default="")

JAZZMIN_SETTINGS = {
    "site_title": "COMEX Admin",
    "site_header": "Mecanizados Gabriel S.A.",
    "site_brand": "COMEX",
    "site_logo": "img/logo.png",
    "login_logo": "img/logo.png",
    "site_logo_classes": "img-circle elevation-3 p-1 bg-white",
    "site_logo_width": 35,
    "login_logo_classes": "img-circle elevation-3 p-3 bg-white",
    "site_icon": "img/logo.png",
    "welcome_sign": "Bienvenido al Sistema COMEX",
    "copyright": "Mecanizados Gabriel S.A.",
    "show_sidebar": True,
    "navigation_expanded": True,
    "hide_apps": ["stock", "proveedores"],
    "hide_models": [
        "productos.proveedor",
        "productos.sector",
        "importaciones.itemimportacion",
        "proveedores.pago",
        "proveedores.fichaproveedor",
        "anmat.tramiteanmat",
        "proveedores.comunicacion",
    ],
    "icons": {
        "auth": "fas fa-users-cog",
        "usuarios.usuario": "fas fa-user",
        "productos.producto": "fas fa-box",
        "productos.sector": "fas fa-building",
        "productos.proveedor": "fas fa-truck",
        "importaciones.importacion": "fas fa-ship",
        "importaciones.itemimportacion": "fas fa-list",
        "anmat.tramiteanmat": "fas fa-file-medical",
        "eventos.eventoextraordinario": "fas fa-exclamation-triangle",
        "eventos.alertaproveedor": "fas fa-bell",
        "proveedores.fichaproveedor": "fas fa-address-card",
        "proveedores.comunicacion": "fas fa-envelope",
        "proveedores.pago": "fas fa-dollar-sign",
        "planificacion.proyeccionagotamiento": "fas fa-chart-line",
        "direccion.dashboard": "fas fa-tachometer-alt",
    },
    "custom_links": {
        "importaciones": [
            {
                "name": "Pagos",
                "url": "/admin/proveedores/pago/",
                "icon": "fas fa-dollar-sign",
                "permissions": ["auth.view_user"],
            },
            {
                "name": "Tramites ANMAT",
                "url": "/admin/anmat/tramiteanmat/",
                "icon": "fas fa-file-medical",
                "permissions": ["auth.view_user"],
            },
            {
                "name": "Comunicaciones",
                "url": "/admin/proveedores/comunicacion/",
                "icon": "fas fa-envelope",
                "permissions": ["auth.view_user"],
            },
        ],
        "productos": [
            {
                "name": "Proveedores",
                "url": "/admin/productos/proveedor/",
                "icon": "fas fa-truck",
                "permissions": ["auth.view_user"],
            },
        ],
        "proveedores": [],
        "direccion": [
            {
                "name": "Reset datos demo",
                "url": "/admin/direccion/dashboard/reset-demo/",
                "icon": "fas fa-trash-alt",
                "permissions": ["auth.change_user"],
            },
        ],
    },
    "default_icon_parents": "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-circle",
    "order_with_respect_to": [
        "importaciones",
        "productos",
        "planificacion",
        "usuarios",
        "eventos",
        "direccion",
    ],
    "topmenu_links": [
        {"name": "Inicio", "url": "admin:index", "permissions": ["auth.view_user"]},
        {"name": "Dashboard", "url": "/dashboard/", "permissions": ["auth.view_user"]},
        {"name": "Importar datos", "url": "/importador/", "permissions": ["auth.view_user"]},
    ],
    "show_ui_builder": False,
    "changeform_format": "horizontal_tabs",
    "language_chooser": False,
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-dark",
    "accent": "accent-primary",
    "navbar": "navbar-dark",
    "no_navbar_border": False,
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-dark-primary",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "default",
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success",
    },
}
