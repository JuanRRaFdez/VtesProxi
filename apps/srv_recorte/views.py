from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile


@csrf_exempt
def recortar_imagen(request):
    if request.method == "POST" and request.FILES.get("imagen"):
        imagen = request.FILES["imagen"]
        destino = (request.POST.get("destino") or "cripta").strip().lower()
        base_path = (
            "/libreria/importar-imagen/" if destino == "libreria" else "/cripta/importar-imagen/"
        )
        path = default_storage.save(f"recortes/{imagen.name}", ContentFile(imagen.read()))
        return redirect(f"{base_path}?recorte={path}")
    return render(request, "srv_recorte/recortar_imagen.html")
