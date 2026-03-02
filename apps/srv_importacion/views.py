from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

# Create your views here.

class ImagenImportacionView(APIView):
    def post(self, request, format=None):
        imagen = request.FILES.get('imagen')
        if not imagen:
            return Response({'error': 'No se envió ninguna imagen.'}, status=status.HTTP_400_BAD_REQUEST)
        path = default_storage.save(f"imagenes/{imagen.name}", ContentFile(imagen.read()))
        return Response({'mensaje': 'Imagen importada correctamente.', 'ruta': path}, status=status.HTTP_201_CREATED)
