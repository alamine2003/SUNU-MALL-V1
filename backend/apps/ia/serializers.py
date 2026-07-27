from rest_framework import serializers
from .models import RecommendationLog


class RecommendationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecommendationLog
        fields = ["id", "user", "payload", "created_at"]
        read_only_fields = ["id", "created_at"]


class GenerateDescriptionSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    category = serializers.IntegerField(required=False, allow_null=True)
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    store = serializers.UUIDField()


class ChatMessageSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=["user", "assistant"])
    content = serializers.CharField()


class ChatSerializer(serializers.Serializer):
    message = serializers.CharField(max_length=2000)
    history = ChatMessageSerializer(many=True, required=False, default=list)
