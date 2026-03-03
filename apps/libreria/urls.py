from django.urls import path
from .views import importar_imagen

urlpatterns = [
    path('importar-imagen/', importar_imagen, name='importar_imagen_libreria'),
]
