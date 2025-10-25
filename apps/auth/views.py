from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.contrib.auth.models import User
import logging

logger = logging.getLogger(__name__)

@csrf_protect
@require_http_methods(["GET", "POST"])
def login_view(request):
    """View para página de login"""
    if request.method == 'GET':
        # Se já está logado, redirecionar para a página principal
        if request.user.is_authenticated:
            return redirect('/interjornada/')
        return render(request, 'auth/login.html')
    
    elif request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if not username or not password:
            messages.error(request, 'Usuário e senha são obrigatórios')
            return render(request, 'auth/login.html')
        
        # Autenticar usuário
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            if user.is_active:
                login(request, user)
                logger.info(f'Login bem-sucedido para usuário: {username}')
                
                # Redirecionar para a página principal
                return redirect('/interjornada/')
            else:
                messages.error(request, 'Conta desativada')
                logger.warning(f'Tentativa de login com conta desativada: {username}')
        else:
            messages.error(request, 'Usuário ou senha incorretos')
            logger.warning(f'Tentativa de login falhada para usuário: {username}')
        
        return render(request, 'auth/login.html')

@login_required
def logout_view(request):
    """View para logout"""
    username = request.user.username
    logout(request)
    logger.info(f'Logout realizado para usuário: {username}')
    return redirect('/login/')

@login_required
def protected_view(request):
    """View protegida para testar autenticação"""
    return JsonResponse({
        'authenticated': True,
        'user': request.user.username,
        'message': 'Acesso autorizado'
    })

def create_default_user():
    """Criar usuário padrão se não existir"""
    if not User.objects.filter(username='admin').exists():
        User.objects.create_user(
            username='admin',
            password='admin123',
            is_staff=True,
            is_superuser=True
        )
        logger.info('Usuário padrão criado: admin/admin123')

