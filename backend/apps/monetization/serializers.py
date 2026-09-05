from rest_framework import serializers
from .models import (
    Notification, SponsoredProduct, SubscriptionPlan,
    Subscription, Invoice
)


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "user", "channel", "subject", "message", "status", "is_read", "sent_at", "created_at"]
        read_only_fields = ["id", "created_at"]


class SponsoredProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = SponsoredProduct
        fields = [
            "id", "product", "store", "daily_budget", 
            "starts_at", "ends_at", "status", "created_at", "updated_at"
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate(self, attrs):
        daily_budget = attrs.get("daily_budget")
        starts_at = attrs.get("starts_at")
        ends_at = attrs.get("ends_at")
        if daily_budget is not None and daily_budget <= 0:
            raise serializers.ValidationError({"daily_budget": "Le budget quotidien doit être positif."})
        if starts_at and ends_at and starts_at > ends_at:
            raise serializers.ValidationError({"ends_at": "La date de fin doit suivre la date de début."})
        if self.instance:
            if "product" in attrs and attrs["product"] != self.instance.product:
                raise serializers.ValidationError({"product": "Le produit d'une campagne ne peut pas être changé."})
            if "store" in attrs and attrs["store"] != self.instance.store:
                raise serializers.ValidationError({"store": "La boutique d'une campagne ne peut pas être changée."})
        return attrs


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = ["id", "name", "price", "billing_cycle", "features", "max_products", "created_at"]
        read_only_fields = ["id", "created_at"]


class SubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = [
            "id", "plan", "subscriber_type", "subscriber_id",
            "status", "starts_at", "ends_at", "created_at", "updated_at"
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = [
            "id", "subscription", "amount", "status",
            "issued_at", "due_at", "paid_at", "created_at", "updated_at"
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
