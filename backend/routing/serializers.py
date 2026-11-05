from datetime import timezone

from rest_framework import serializers


class AnalyzeRequestSerializer(serializers.Serializer):
    origin = serializers.CharField(allow_blank=False, trim_whitespace=True)
    destination = serializers.CharField(allow_blank=False, trim_whitespace=True)
    departure_time = serializers.DateTimeField(default_timezone=timezone.utc)
    load_weight_lb = serializers.IntegerField(min_value=1, max_value=150000)
    interval_miles = serializers.ChoiceField(
        choices=(10, 25, 50), default=25
    )

    def validate(self, attrs):
        if attrs["origin"].casefold() == attrs["destination"].casefold():
            raise serializers.ValidationError(
                {"destination": "Origin and destination must be different."}
            )
        return attrs