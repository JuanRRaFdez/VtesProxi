from django.urls import path
from . import views

app_name = "mis_cartas"

urlpatterns = [
    path('', views.mis_cartas, name='mis_cartas'),
    path('descargar/<str:filename>/', views.descargar_carta, name='descargar_carta'),
    path('borrar/<str:filename>/', views.borrar_carta, name='borrar_carta'),
    path('generar-pdf/', views.generar_pdf_cartas, name='generar_pdf_cartas'),
]
