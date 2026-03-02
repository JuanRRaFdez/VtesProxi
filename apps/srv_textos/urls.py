from django.urls import path
from . import views

urlpatterns = [
    path('render-texto/', views.render_texto, name='render_texto'),
    path('render-nombre/', views.render_nombre, name='render_nombre'),
    path('render-clan/', views.render_clan, name='render_clan'),
    path('guardar-carta/', views.guardar_carta, name='guardar_carta'),
]
