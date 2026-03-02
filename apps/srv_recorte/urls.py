from django.urls import path
from .views import recortar_imagen

urlpatterns = [
    path('recortar-imagen/', recortar_imagen, name='recortar_imagen'),
]
