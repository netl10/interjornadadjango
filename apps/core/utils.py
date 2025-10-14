"""
Utilitários para tratamento de timezone e conversões de data/hora.
Sempre trabalhamos com UTC internamente e convertemos para exibição.
"""
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class TimezoneUtils:
    """Utilitários para manipulação de timezone."""
    
    # Timezone UTC (sempre usar internamente)
    UTC = timezone.utc
    
    # Timezone de exibição (configurável)
    DISPLAY_TZ = timezone.get_default_timezone()
    
    @classmethod
    def get_utc_now(cls):
        """Retorna o datetime atual em UTC."""
        return datetime.now(cls.UTC)
    
    @classmethod
    def get_display_now(cls):
        """Retorna o datetime atual no timezone de exibição."""
        return datetime.now(cls.DISPLAY_TZ)
    
    @classmethod
    def utc_to_display(cls, utc_datetime):
        """
        Converte datetime UTC para timezone de exibição.
        
        Args:
            utc_datetime: datetime em UTC
            
        Returns:
            datetime no timezone de exibição
        """
        if utc_datetime is None:
            return None
            
        if utc_datetime.tzinfo is None:
            # Se não tem timezone, assume UTC
            utc_datetime = utc_datetime.replace(tzinfo=cls.UTC)
        
        return utc_datetime.astimezone(cls.DISPLAY_TZ)
    
    @classmethod
    def display_to_utc(cls, display_datetime):
        """
        Converte datetime do timezone de exibição para UTC.
        
        Args:
            display_datetime: datetime no timezone de exibição
            
        Returns:
            datetime em UTC
        """
        if display_datetime is None:
            return None
            
        if display_datetime.tzinfo is None:
            # Se não tem timezone, assume que é do timezone de exibição
            display_datetime = cls.DISPLAY_TZ.localize(display_datetime)
        
        return display_datetime.astimezone(cls.UTC)
    
    @classmethod
    def format_datetime(cls, utc_datetime, format_str='%d/%m/%Y %H:%M:%S'):
        """
        Formata datetime UTC para string no timezone de exibição.
        
        Args:
            utc_datetime: datetime em UTC
            format_str: formato da string
            
        Returns:
            string formatada
        """
        if utc_datetime is None:
            return None
            
        # Se o datetime é ingênuo (sem timezone), assumir que já está no timezone de exibição
        if timezone.is_aware(utc_datetime):
            # Converter de UTC para timezone de exibição
            display_datetime = utc_datetime.astimezone(cls.DISPLAY_TZ)
            return display_datetime.strftime(format_str)
        else:
            # Se não tem timezone, assumir que já está no horário local
            return utc_datetime.strftime(format_str)
    
    @classmethod
    def parse_datetime(cls, datetime_str, format_str='%d/%m/%Y %H:%M:%S'):
        """
        Converte string de datetime para UTC.
        
        Args:
            datetime_str: string de datetime
            format_str: formato da string
            
        Returns:
            datetime em UTC
        """
        if not datetime_str:
            return None
            
        try:
            # Parse da string assumindo timezone de exibição
            display_datetime = datetime.strptime(datetime_str, format_str)
            display_datetime = cls.DISPLAY_TZ.localize(display_datetime)
            return cls.display_to_utc(display_datetime)
        except ValueError as e:
            logger.error(f"Erro ao fazer parse do datetime '{datetime_str}': {e}")
            return None
    
    @classmethod
    def get_time_remaining(cls, end_time_utc):
        """
        Calcula tempo restante até um datetime UTC.
        
        Args:
            end_time_utc: datetime final em UTC
            
        Returns:
            dict com tempo restante formatado
        """
        if end_time_utc is None:
            return None
            
        now_utc = cls.get_utc_now()
        time_diff = end_time_utc - now_utc
        
        if time_diff.total_seconds() <= 0:
            return {
                'total_seconds': 0,
                'formatted': 'Expirado',
                'is_expired': True
            }
        
        total_seconds = int(time_diff.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        if hours > 0:
            formatted = f"{hours}h {minutes:02d}min {seconds:02d}s"
        elif minutes > 0:
            formatted = f"{minutes}min {seconds:02d}s"
        else:
            formatted = f"{seconds}s"
        
        return {
            'total_seconds': total_seconds,
            'formatted': formatted,
            'is_expired': False,
            'hours': hours,
            'minutes': minutes,
            'seconds': seconds
        }
    
    @classmethod
    def add_minutes(cls, utc_datetime, minutes):
        """
        Adiciona minutos a um datetime UTC.
        
        Args:
            utc_datetime: datetime em UTC
            minutes: minutos a adicionar
            
        Returns:
            datetime em UTC
        """
        if utc_datetime is None:
            return None
            
        return utc_datetime + timedelta(minutes=minutes)
    
    @classmethod
    def add_hours(cls, utc_datetime, hours):
        """
        Adiciona horas a um datetime UTC.
        
        Args:
            utc_datetime: datetime em UTC
            hours: horas a adicionar
            
        Returns:
            datetime em UTC
        """
        if utc_datetime is None:
            return None
            
        return utc_datetime + timedelta(hours=hours)


class SystemUtils:
    """Utilitários gerais do sistema."""
    
    @staticmethod
    def get_system_info():
        """Retorna informações do sistema."""
        return {
            'timezone_offset': settings.TIMEZONE_OFFSET,
            'display_timezone': settings.DISPLAY_TIMEZONE,
            'work_duration_minutes': settings.WORK_DURATION_MINUTES,
            'rest_duration_minutes': settings.REST_DURATION_MINUTES,
            'monitor_interval': settings.MONITOR_INTERVAL_SECONDS,
            'exemption_group': settings.EXEMPTION_GROUP_NAME,
        }
    
    @staticmethod
    def format_duration(minutes):
        """
        Formata duração em minutos para string legível.
        
        Args:
            minutes: duração em minutos
            
        Returns:
            string formatada
        """
        if minutes < 60:
            return f"{minutes}min"
        
        hours = minutes // 60
        remaining_minutes = minutes % 60
        
        if remaining_minutes == 0:
            return f"{hours}h"
        else:
            return f"{hours}h {remaining_minutes}min"
    
    @staticmethod
    def get_work_duration_formatted():
        """Retorna duração de trabalho formatada."""
        return SystemUtils.format_duration(settings.WORK_DURATION_MINUTES)
    
    @staticmethod
    def get_rest_duration_formatted():
        """Retorna duração de interjornada formatada."""
        return SystemUtils.format_duration(settings.REST_DURATION_MINUTES)


class ValidationUtils:
    """Utilitários para validação."""
    
    @staticmethod
    def is_valid_ip(ip):
        """Valida se um IP é válido."""
        import ipaddress
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def is_valid_port(port):
        """Valida se uma porta é válida."""
        try:
            port = int(port)
            return 1 <= port <= 65535
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def is_valid_user_id(user_id):
        """Valida se um ID de usuário é válido."""
        try:
            user_id = int(user_id)
            return user_id > 0
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def sanitize_string(text):
        """Sanitiza string removendo caracteres perigosos."""
        if not text:
            return ""
        
        # Remove caracteres de controle e HTML
        import re
        text = re.sub(r'[<>"\']', '', str(text))
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        
        return text.strip()


class CacheUtils:
    """Utilitários para cache."""
    
    @staticmethod
    def get_cache_key(prefix, *args):
        """
        Gera chave de cache consistente.
        
        Args:
            prefix: prefixo da chave
            *args: argumentos para formar a chave
            
        Returns:
            string da chave de cache
        """
        key_parts = [str(prefix)]
        key_parts.extend(str(arg) for arg in args)
        return ':'.join(key_parts)
    
    @staticmethod
    def get_user_cache_key(user_id, action):
        """Gera chave de cache para usuário."""
        return CacheUtils.get_cache_key('user', user_id, action)
    
    @staticmethod
    def get_device_cache_key(device_ip, action):
        """Gera chave de cache para dispositivo."""
        return CacheUtils.get_cache_key('device', device_ip, action)
    
    @staticmethod
    def get_system_cache_key(action):
        """Gera chave de cache para sistema."""
        return CacheUtils.get_cache_key('system', action)
