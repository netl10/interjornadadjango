"""
Serializers para o app devices.
"""
from rest_framework import serializers
from .models import Device, DeviceLog, DeviceSession, DeviceConfiguration


class DeviceConfigurationSerializer(serializers.ModelSerializer):
    """Serializer para configurações de dispositivos."""
    
    class Meta:
        model = DeviceConfiguration
        fields = [
            'id', 'monitor_interval', 'log_retention_days', 'api_endpoints',
            'authentication_method', 'data_format', 'encoding',
            'cache_enabled', 'cache_duration', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class DeviceSerializer(serializers.ModelSerializer):
    """Serializer para dispositivos."""
    
    base_url = serializers.ReadOnlyField()
    is_connected = serializers.ReadOnlyField()
    connection_success_rate = serializers.ReadOnlyField()
    configuration = DeviceConfigurationSerializer(read_only=True)
    
    class Meta:
        model = Device
        fields = [
            'id', 'name', 'device_type', 'ip_address', 'port', 'username',
            'password', 'use_https', 'status', 'is_enabled',
            'connection_timeout', 'request_timeout', 'max_reconnection_attempts',
            'last_connection', 'last_error', 'error_count', 'success_count',
            'base_url', 'is_connected', 'connection_success_rate',
            'configuration', 'created_at', 'updated_at', 'created_by'
        ]
        read_only_fields = [
            'last_connection', 'last_error', 'error_count', 'success_count',
            'created_at', 'updated_at', 'created_by'
        ]
        extra_kwargs = {
            'password': {'write_only': True}
        }
    
    def validate_ip_address(self, value):
        """Valida endereço IP."""
        from apps.core.utils import ValidationUtils
        if not ValidationUtils.is_valid_ip(value):
            raise serializers.ValidationError("Endereço IP inválido")
        return value
    
    def validate_port(self, value):
        """Valida porta."""
        from apps.core.utils import ValidationUtils
        if not ValidationUtils.is_valid_port(value):
            raise serializers.ValidationError("Porta inválida")
        return value
    
    def validate_name(self, value):
        """Valida nome do dispositivo."""
        if not value or len(value.strip()) < 2:
            raise serializers.ValidationError("Nome deve ter pelo menos 2 caracteres")
        return value.strip()


class DeviceLogSerializer(serializers.ModelSerializer):
    """Serializer para logs de dispositivos."""
    
    device_name = serializers.CharField(source='device.name', read_only=True)
    device_ip = serializers.CharField(source='device.ip_address', read_only=True)
    
    class Meta:
        model = DeviceLog
        fields = [
            'id', 'device', 'device_name', 'device_ip', 'log_type', 'level',
            'message', 'details', 'timestamp'
        ]
        read_only_fields = ['timestamp']


class DeviceSessionSerializer(serializers.ModelSerializer):
    """Serializer para sessões de dispositivos."""
    
    device_name = serializers.CharField(source='device.name', read_only=True)
    device_ip = serializers.CharField(source='device.ip_address', read_only=True)
    duration = serializers.ReadOnlyField()
    success_rate = serializers.ReadOnlyField()
    
    class Meta:
        model = DeviceSession
        fields = [
            'id', 'device', 'device_name', 'device_ip', 'session_token',
            'is_active', 'started_at', 'ended_at', 'last_activity',
            'requests_count', 'errors_count', 'duration', 'success_rate'
        ]
        read_only_fields = [
            'started_at', 'ended_at', 'last_activity', 'requests_count', 'errors_count'
        ]
        extra_kwargs = {
            'session_token': {'write_only': True}
        }


class DeviceConnectionSerializer(serializers.Serializer):
    """Serializer para conexão com dispositivo."""
    
    device_id = serializers.IntegerField()
    
    def validate_device_id(self, value):
        """Valida ID do dispositivo."""
        from apps.core.utils import ValidationUtils
        if not ValidationUtils.is_valid_user_id(value):
            raise serializers.ValidationError("ID do dispositivo inválido")
        return value


class DeviceConnectionResponseSerializer(serializers.Serializer):
    """Serializer para resposta de conexão com dispositivo."""
    
    success = serializers.BooleanField()
    message = serializers.CharField()
    token = serializers.CharField(allow_null=True)
    connected_at = serializers.DateTimeField(allow_null=True)


class DeviceLogsRequestSerializer(serializers.Serializer):
    """Serializer para requisição de logs de dispositivo."""
    
    device_id = serializers.IntegerField()
    limit = serializers.IntegerField(default=100, min_value=1, max_value=1000)
    
    def validate_device_id(self, value):
        """Valida ID do dispositivo."""
        from apps.core.utils import ValidationUtils
        if not ValidationUtils.is_valid_user_id(value):
            raise serializers.ValidationError("ID do dispositivo inválido")
        return value


class DeviceLogsResponseSerializer(serializers.Serializer):
    """Serializer para resposta de logs de dispositivo."""
    
    success = serializers.BooleanField()
    message = serializers.CharField()
    logs = serializers.ListField()
    count = serializers.IntegerField()


class DeviceStatusResponseSerializer(serializers.Serializer):
    """Serializer para resposta de status de dispositivo."""
    
    success = serializers.BooleanField()
    message = serializers.CharField()
    device_status = serializers.CharField()
    is_connected = serializers.BooleanField()
    last_connection = serializers.DateTimeField(allow_null=True)
    connection_success_rate = serializers.FloatField()
    status_data = serializers.DictField()


class DeviceUsersResponseSerializer(serializers.Serializer):
    """Serializer para resposta de usuários de dispositivo."""
    
    success = serializers.BooleanField()
    message = serializers.CharField()
    users = serializers.ListField()
    count = serializers.IntegerField()


class DeviceGroupsResponseSerializer(serializers.Serializer):
    """Serializer para resposta de grupos de dispositivo."""
    
    success = serializers.BooleanField()
    message = serializers.CharField()
    groups = serializers.ListField()
    count = serializers.IntegerField()


class MonitoringStatusSerializer(serializers.Serializer):
    """Serializer para status de monitoramento."""
    
    monitoring_active = serializers.BooleanField()
    stats = serializers.DictField()
    timestamp = serializers.DateTimeField()


class DeviceStatusSummarySerializer(serializers.Serializer):
    """Serializer para resumo de status de dispositivos."""
    
    id = serializers.IntegerField()
    name = serializers.CharField()
    device_type = serializers.CharField()
    ip_address = serializers.CharField()
    port = serializers.IntegerField()
    status = serializers.CharField()
    is_enabled = serializers.BooleanField()
    is_connected = serializers.BooleanField()
    last_connection = serializers.DateTimeField(allow_null=True)
    last_error = serializers.DateTimeField(allow_null=True)
    error_count = serializers.IntegerField()
    success_count = serializers.IntegerField()
    connection_success_rate = serializers.FloatField()
    active_session = serializers.DictField(allow_null=True)


class AllDevicesStatusResponseSerializer(serializers.Serializer):
    """Serializer para resposta de status de todos os dispositivos."""
    
    devices = DeviceStatusSummarySerializer(many=True)
    total_count = serializers.IntegerField()
    active_count = serializers.IntegerField()
    error_count = serializers.IntegerField()
    timestamp = serializers.DateTimeField()
