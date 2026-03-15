from django.urls import path
from . import views

app_name = 'importaciones'

urlpatterns = [
    path('importaciones/', views.lista_importaciones, name='lista'),
    path('importaciones/<int:pk>/cambiar-estado/', views.cambiar_estado, name='cambiar_estado'),
]
