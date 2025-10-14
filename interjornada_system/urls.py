"""
URL configuration for interjornada_system project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
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
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # URLs específicas do admin devem vir ANTES da URL genérica do admin
    path('admin/logs/', include('apps.logs.urls')),  # URLs do admin para logs
    path('admin/sessions/', include('apps.employee_sessions.urls')),  # URLs do admin para sessões
    path('admin/core/', include('apps.core.urls')),  # URLs do admin para configurações
    path('admin/', admin.site.urls),  # URL genérica do admin por último
    path('api/v1/', include('apps.core.urls')),
    path('api/v1/devices/', include('apps.devices.urls')),
    path('api/v1/employees/', include('apps.employees.urls')),
    path('api/v1/logs/', include('apps.logs.urls')),
    path('api/v1/interjornada/', include('apps.interjornada.urls')),
    path('api/v1/dashboard/', include('apps.dashboard.urls')),
    # Página principal de interjornada
    path('', include('apps.employee_sessions.urls')),
]

# Servir arquivos estáticos e media em desenvolvimento
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
