from django.urls import path
from . import views

app_name = "usuarios"

urlpatterns = [
    path('mis-cartas/', views.mis_cartas, name='mis_cartas'),
]
