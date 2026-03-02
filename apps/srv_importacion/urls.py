from django.urls import path
from .views import ImagenImportacionView

urlpatterns = [
    path('importar-imagen/', ImagenImportacionView.as_view(), name='importar_imagen'),
]
