"""
Serializers para o app interjornada.
"""
from rest_framework import serializers
from .models import InterjornadaRule, InterjornadaCycle, InterjornadaViolation, InterjornadaStatistics


class InterjornadaRuleSerializer(serializers.ModelSerializer):
    """Serializer para regras de interjornada."""
    
    work_duration_formatted = serializers.ReadOnlyField()
    rest_duration_formatted = serializers.ReadOnlyField()
    
    class Meta:
        model = InterjornadaRule
        fields = [
            'id', 'name', 'description', 'is_active', 'work_duration_minutes', 'rest_duration_minutes',
            'apply_to_all', 'employee_groups', 'exempt_employee_groups', 'start_time', 'end_time',
            'days_of_week', 'work_duration_formatted', 'rest_duration_formatted',
            'created_at', 'updated_at', 'created_by'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by']
    
    def validate_work_duration_minutes(self, value):
        """Valida duração de trabalho."""
        if value <= 0:
            raise serializers.ValidationError("Duração de trabalho deve ser maior que zero")
        if value > 1440:  # 24 horas
            raise serializers.ValidationError("Duração de trabalho não pode exceder 24 horas")
        return value
    
    def validate_rest_duration_minutes(self, value):
        """Valida duração de interjornada."""
        if value <= 0:
            raise serializers.ValidationError("Duração de interjornada deve ser maior que zero")
        if value > 1440:  # 24 horas
            raise serializers.ValidationError("Duração de interjornada não pode exceder 24 horas")
        return value
    
    def validate_name(self, value):
        """Valida nome da regra."""
        if not value or len(value.strip()) < 2:
            raise serializers.ValidationError("Nome deve ter pelo menos 2 caracteres")
        return value.strip()


class InterjornadaCycleSerializer(serializers.ModelSerializer):
    """Serializer para ciclos de interjornada."""
    
    employee_name = serializers.CharField(source='employee.name', read_only=True)
    employee_device_id = serializers.IntegerField(source='employee.device_id', read_only=True)
    rule_name = serializers.CharField(source='rule.name', read_only=True)
    work_time_remaining = serializers.ReadOnlyField()
    rest_time_remaining = serializers.ReadOnlyField()
    is_active = serializers.ReadOnlyField()
    is_work_period = serializers.ReadOnlyField()
    is_rest_period = serializers.ReadOnlyField()
    can_start_work = serializers.ReadOnlyField()
    should_start_rest = serializers.ReadOnlyField()
    
    class Meta:
        model = InterjornadaCycle
        fields = [
            'id', 'employee', 'employee_name', 'employee_device_id', 'rule', 'rule_name',
            'current_state', 'cycle_start', 'work_start', 'work_end', 'rest_start', 'rest_end',
            'actual_work_duration_minutes', 'actual_rest_duration_minutes',
            'work_time_remaining', 'rest_time_remaining', 'is_active', 'is_work_period',
            'is_rest_period', 'can_start_work', 'should_start_rest', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'cycle_start', 'work_start', 'work_end', 'rest_start', 'rest_end',
            'actual_work_duration_minutes', 'actual_rest_duration_minutes',
            'created_at', 'updated_at'
        ]
    
    def validate_employee(self, value):
        """Valida funcionário."""
        if not value.is_active:
            raise serializers.ValidationError("Funcionário deve estar ativo")
        return value
    
    def validate_current_state(self, value):
        """Valida estado do ciclo."""
        valid_states = [choice[0] for choice in InterjornadaCycle.CYCLE_STATES]
        if value not in valid_states:
            raise serializers.ValidationError(f"Estado deve ser um dos seguintes: {', '.join(valid_states)}")
        return value


class InterjornadaViolationSerializer(serializers.ModelSerializer):
    """Serializer para violações de interjornada."""
    
    employee_name = serializers.CharField(source='cycle.employee.name', read_only=True)
    employee_device_id = serializers.IntegerField(source='cycle.employee.device_id', read_only=True)
    cycle_id = serializers.IntegerField(source='cycle.id', read_only=True)
    display_violation_time = serializers.ReadOnlyField()
    display_detected_time = serializers.ReadOnlyField()
    resolved_by_name = serializers.CharField(source='resolved_by.username', read_only=True)
    
    class Meta:
        model = InterjornadaViolation
        fields = [
            'id', 'cycle', 'cycle_id', 'employee_name', 'employee_device_id',
            'violation_type', 'severity', 'description', 'details',
            'violation_time', 'detected_time', 'display_violation_time', 'display_detected_time',
            'action_taken', 'resolved', 'resolved_at', 'resolved_by', 'resolved_by_name'
        ]
        read_only_fields = [
            'violation_time', 'detected_time', 'resolved_at', 'resolved_by'
        ]
    
    def validate_violation_type(self, value):
        """Valida tipo de violação."""
        valid_types = [choice[0] for choice in InterjornadaViolation.VIOLATION_TYPES]
        if value not in valid_types:
            raise serializers.ValidationError(f"Tipo deve ser um dos seguintes: {', '.join(valid_types)}")
        return value
    
    def validate_severity(self, value):
        """Valida severidade."""
        valid_severities = [choice[0] for choice in InterjornadaViolation.SEVERITY_LEVELS]
        if value not in valid_severities:
            raise serializers.ValidationError(f"Severidade deve ser uma das seguintes: {', '.join(valid_severities)}")
        return value


class InterjornadaStatisticsSerializer(serializers.ModelSerializer):
    """Serializer para estatísticas de interjornada."""
    
    employee_name = serializers.CharField(source='employee.name', read_only=True)
    employee_device_id = serializers.IntegerField(source='employee.device_id', read_only=True)
    completion_rate = serializers.ReadOnlyField()
    violation_rate = serializers.ReadOnlyField()
    work_time_formatted = serializers.ReadOnlyField()
    rest_time_formatted = serializers.ReadOnlyField()
    
    class Meta:
        model = InterjornadaStatistics
        fields = [
            'id', 'employee', 'employee_name', 'employee_device_id', 'date',
            'total_cycles', 'completed_cycles', 'cancelled_cycles',
            'total_work_time_minutes', 'total_rest_time_minutes',
            'average_work_time_minutes', 'average_rest_time_minutes',
            'total_violations', 'resolved_violations', 'critical_violations',
            'completion_rate', 'violation_rate', 'work_time_formatted', 'rest_time_formatted',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class InterjornadaStatusSerializer(serializers.Serializer):
    """Serializer para status de interjornada."""
    
    has_active_cycle = serializers.BooleanField()
    can_access = serializers.BooleanField()
    message = serializers.CharField()
    next_action = serializers.CharField()
    cycle_state = serializers.CharField(allow_null=True)
    time_remaining = serializers.DictField(allow_null=True)


class InterjornadaEventSerializer(serializers.Serializer):
    """Serializer para eventos de interjornada."""
    
    event_type = serializers.IntegerField()
    timestamp = serializers.DateTimeField()
    
    def validate_event_type(self, value):
        """Valida tipo de evento."""
        if value not in [1, 2]:  # 1=entrada, 2=saída
            raise serializers.ValidationError("Tipo de evento deve ser 1 (entrada) ou 2 (saída)")
        return value


class InterjornadaEventResponseSerializer(serializers.Serializer):
    """Serializer para resposta de eventos de interjornada."""
    
    success = serializers.BooleanField()
    message = serializers.CharField()
    action = serializers.CharField()
    cycle_state = serializers.CharField(allow_null=True)
    time_remaining = serializers.DictField(allow_null=True)


class InterjornadaMonitoringStatsSerializer(serializers.Serializer):
    """Serializer para estatísticas de monitoramento."""
    
    status = serializers.CharField()
    total_active_cycles = serializers.IntegerField()
    work_cycles = serializers.IntegerField()
    rest_cycles = serializers.IntegerField()
    violations_detected = serializers.IntegerField()
    cycles_completed = serializers.IntegerField()
    errors = serializers.ListField(child=serializers.CharField())


class InterjornadaViolationResolveSerializer(serializers.Serializer):
    """Serializer para resolução de violações."""
    
    action_taken = serializers.CharField(max_length=500)
    
    def validate_action_taken(self, value):
        """Valida ação tomada."""
        if not value or len(value.strip()) < 5:
            raise serializers.ValidationError("Ação tomada deve ter pelo menos 5 caracteres")
        return value.strip()


class InterjornadaViolationsSummarySerializer(serializers.Serializer):
    """Serializer para resumo de violações."""
    
    total_unresolved = serializers.IntegerField()
    severity_counts = serializers.DictField()
    type_counts = serializers.DictField()
    critical_violations = serializers.IntegerField()
    high_violations = serializers.IntegerField()
