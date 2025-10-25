from django.shortcuts import redirect
from django.urls import reverse
from django.http import JsonResponse
from django.contrib.auth import logout
import logging

logger = logging.getLogger(__name__)

class AuthMiddleware:
    """Middleware para proteger APIs e rotas sensíveis"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Rotas que NÃO precisam de autenticação
        public_paths = [
            '/login/',
            '/static/',
            '/media/',
            '/favicon.ico',
            '/admin/login/',
        ]
        
        # Verificar se a rota é pública
        is_public = any(request.path.startswith(path) for path in public_paths)
        
        # Se não for rota pública e usuário não estiver autenticado
        if not is_public and not request.user.is_authenticated:
            logger.warning(f'Tentativa de acesso não autorizado: {request.path} - IP: {request.META.get("REMOTE_ADDR")}')
            
            # Se for uma requisição AJAX/API, retornar JSON
            if request.path.startswith('/api/'):
                return JsonResponse({
                    'error': 'Authentication required',
                    'message': 'Você precisa fazer login para acessar esta funcionalidade',
                    'redirect': '/login/'
                }, status=401)
            
            # Para outras rotas, redirecionar para login
            return redirect('/login/')
        
        # Se usuário estiver autenticado mas tentar acessar login, redirecionar para home
        if request.path == '/login/' and request.user.is_authenticated:
            return redirect('/interjornada/')
        
        response = self.get_response(request)
        return response
