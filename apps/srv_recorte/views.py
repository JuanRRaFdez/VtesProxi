from django.shortcuts import render, redirect
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

@csrf_exempt
def recortar_imagen(request):
    imagen_url = None
    if request.method == 'POST' and request.FILES.get('imagen'):
        imagen = request.FILES['imagen']
        path = default_storage.save(f"recortes/{imagen.name}", ContentFile(imagen.read()))
        # Redirigir a la página principal de cripta mostrando el recorte
        return redirect(f'/cripta/importar-imagen/?recorte={path}')
    return render(request, 'srv_recorte/recortar_imagen.html')
