from django.urls import path

from apps.layouts import views

app_name = 'layouts'

urlpatterns = [
    path('', views.editor, name='editor'),
]
