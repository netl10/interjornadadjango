"""
Serializers para o app logs.
"""
from rest_framework import serializers
from .models import AccessLog, SystemLog, LogProcessingQueue


class AccessLogSerializer(serializers.ModelSerializer):
    """Serializer para logs de acesso."""
    
    display_device_timestamp = serializers.ReadOnlyField()
    display_received_timestamp = serializers.ReadOnlyField()
    display_processed_timestamp = serializers.ReadOnlyField()
    is_processed = serializers.ReadOnlyField()
    is_pending = serializers.ReadOnlyField()
    has_error = serializers.ReadOnlyField()
    
    class Meta:
        model = AccessLog
        fields = [
            'id', 'device_log_id', 'user_id', 'user_name', 'event_type',
            'event_description', 'device_id', 'device_name', 'portal_id',
            'device_timestamp', 'received_timestamp', 'processed_timestamp',
            'processing_status', 'processing_error', 'raw_data', 'processed_data',
            'is_processed', 'is_pending', 'has_error',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'received_timestamp', 'processed_timestamp', 'created_at', 'updated_at'
        ]


class SystemLogSerializer(serializers.ModelSerializer):
    """Serializer para logs do sistema."""
    
    display_timestamp = serializers.ReadOnlyField()
    
    class Meta:
        model = SystemLog
        fields = [
            'id', 'level', 'category', 'message', 'user_id', 'user_name',
            'device_id', 'device_name', 'details', 'display_timestamp', 'timestamp'
        ]
        read_only_fields = ['timestamp']


class LogProcessingQueueSerializer(serializers.ModelSerializer):
    """Serializer para fila de processamento de logs."""
    
    access_log_device_id = serializers.IntegerField(source='access_log.device_log_id', read_only=True)
    access_log_user_id = serializers.IntegerField(source='access_log.user_id', read_only=True)
    access_log_user_name = serializers.CharField(source='access_log.user_name', read_only=True)
    can_retry = serializers.ReadOnlyField()
    is_ready_for_processing = serializers.ReadOnlyField()
    
    class Meta:
        model = LogProcessingQueue
        fields = [
            'id', 'access_log', 'access_log_device_id', 'access_log_user_id',
            'access_log_user_name', 'status', 'priority', 'attempts', 'max_attempts',
            'last_attempt', 'next_retry', 'error_message', 'error_details',
            'can_retry', 'is_ready_for_processing', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'last_attempt', 'next_retry', 'error_message', 'error_details',
            'created_at', 'updated_at'
        ]
