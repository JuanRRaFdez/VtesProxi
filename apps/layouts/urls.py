from django.urls import path

from apps.layouts import views

app_name = 'layouts'

urlpatterns = [
    path('', views.editor, name='editor'),
    path('api/list', views.api_list, name='api_list'),
    path('api/create', views.api_create, name='api_create'),
    path('api/detail/<int:layout_id>', views.api_detail, name='api_detail'),
    path('api/update-config', views.api_update_config, name='api_update_config'),
]
