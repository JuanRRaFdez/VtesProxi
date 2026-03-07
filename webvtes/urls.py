"""
URL configuration for webvtes project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""


from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.http import HttpResponseRedirect
from django.conf import settings
from django.conf.urls.static import static
from apps.mis_cartas import views as mis_cartas_views

def root_redirect(request):
    return HttpResponseRedirect('/login/')

urlpatterns = [
    path('', root_redirect),
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('importacion/', include('apps.srv_importacion.urls')),
    path('cripta/', include('apps.cripta.urls')),
    path('libreria/', include('apps.libreria.urls')),
    path('mis-cartas/', include('apps.mis_cartas.urls', namespace='mis_cartas')),
    path('pdf/', mis_cartas_views.pdf_workspace, name='pdf_workspace'),
    path('recorte/', include('apps.srv_recorte.urls')),
    path('srv-textos/', include('apps.srv_textos.urls')),
]

# Servir archivos MEDIA en desarrollo
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
