"""
Serializers para o app employees.
"""
from rest_framework import serializers
from .models import Employee, EmployeeGroup


class EmployeeGroupSerializer(serializers.ModelSerializer):
    """Serializer para grupos de funcionários."""
    
    employee_count = serializers.ReadOnlyField()
    
    class Meta:
        model = EmployeeGroup
        fields = [
            'id', 'name', 'description', 'is_exemption_group',
            'work_duration_minutes', 'rest_duration_minutes',
            'employee_count', 'created_at', 'updated_at'
        ]


class EmployeeSerializer(serializers.ModelSerializer):
    """Serializer para funcionários."""
    
    display_name = serializers.ReadOnlyField()
    effective_work_duration = serializers.ReadOnlyField()
    effective_rest_duration = serializers.ReadOnlyField()
    
    class Meta:
        model = Employee
        fields = [
            'id', 'device_id', 'name', 'employee_code', 'is_active', 'is_exempt',
            'groups', 'exemption_groups', 'work_duration_minutes', 'rest_duration_minutes',
            'display_name', 'effective_work_duration', 'effective_rest_duration',
            'created_at', 'updated_at', 'created_by'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by']
    
    def validate_device_id(self, value):
        """Valida ID do dispositivo."""
        if value <= 0:
            raise serializers.ValidationError("ID do dispositivo deve ser maior que zero")
        return value
    
    def validate_name(self, value):
        """Valida nome do funcionário."""
        if not value or len(value.strip()) < 2:
            raise serializers.ValidationError("Nome deve ter pelo menos 2 caracteres")
        return value.strip()




class EmployeeAccessCheckSerializer(serializers.Serializer):
    """Serializer para verificação de acesso de funcionário."""
    
    device_id = serializers.IntegerField()
    
    def validate_device_id(self, value):
        """Valida ID do dispositivo."""
        if value <= 0:
            raise serializers.ValidationError("ID do dispositivo deve ser maior que zero")
        return value


class EmployeeAccessResponseSerializer(serializers.Serializer):
    """Serializer para resposta de verificação de acesso."""
    
    can_access = serializers.BooleanField()
    reason = serializers.CharField()
    return_time = serializers.DateTimeField(allow_null=True)
    employee = EmployeeSerializer()
    session = serializers.DictField(allow_null=True)
    time_remaining = serializers.DictField(allow_null=True)
