from django.shortcuts import redirect
from django.urls import reverse
from django.http import JsonResponse
import logging

logger = logging.getLogger(__name__)

class AuthMiddleware:
    """Middleware para proteger APIs e rotas sensíveis"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Rotas que precisam de autenticação
        protected_paths = [
            '/api/',
            '/interjornada/',
            '/admin/',
        ]
        
        # Verificar se a rota precisa de proteção
        needs_protection = any(request.path.startswith(path) for path in protected_paths)
        
        if needs_protection and not request.user.is_authenticated:
            # Se for uma requisição AJAX/API, retornar JSON
            if request.path.startswith('/api/'):
                return JsonResponse({
                    'error': 'Authentication required',
                    'redirect': '/login/'
                }, status=401)
            
            # Para outras rotas, redirecionar para login
            return redirect('/login/')
        
        response = self.get_response(request)
        return response

