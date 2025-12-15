from rest_framework import serializers
from .models import Order, Payment, Payout
import re

class CreateOrderSerializer(serializers.Serializer):
    buyer_phone = serializers.CharField(max_length=15, required=True)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=True, min_value=1)
    product_description = serializers.CharField(required=True, min_length=5, max_length=1000)
    
    def validate_buyer_phone(self, value):
        """Validate Kenyan phone number format"""
        # Remove any spaces or special characters
        phone = re.sub(r'[^\d+]', '', value)
        
        # Kenyan phone formats: +254..., 254..., 07..., 01...
        if phone.startswith('+254'):
            phone = phone[1:]
        elif phone.startswith('0'):
            phone = '254' + phone[1:]
        elif not phone.startswith('254'):
            raise serializers.ValidationError("Invalid Kenyan phone number format")
        
        if len(phone) != 12:
            raise serializers.ValidationError("Phone number must be 12 digits (254XXXXXXXXX)")
        
        return phone
    
    def validate_amount(self, value):
        """Validate amount is reasonable"""
        if value > 500000:  # 500,000 KES
            raise serializers.ValidationError("Amount exceeds maximum limit")
        return value


class OrderSerializer(serializers.ModelSerializer):
    buyer_phone_masked = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = [
            'id',
            'order_reference',
            'buyer_phone_masked',
            'amount',
            'product_description',
            'status',
            'created_at',
            'updated_at',
            'paid_at',
            'completed_at'
        ]
        read_only_fields = ['id', 'order_reference', 'created_at', 'updated_at']
    
    def get_buyer_phone_masked(self, obj):
        """Return masked phone number"""
        return f"****{obj.buyer_phone_last4}"


class PaymentWebhookSerializer(serializers.Serializer):
    """Serializer for simulated payment webhook"""
    order_reference = serializers.CharField(required=True)
    transaction_id = serializers.CharField(required=True)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    payment_method = serializers.ChoiceField(
        choices=['mpesa', 'stripe', 'visa'],
        default='mpesa'
    )
    payer_phone = serializers.CharField(required=False, allow_blank=True)
    metadata = serializers.JSONField(required=False, default=dict)
    
    def validate_transaction_id(self, value):
        """Ensure transaction ID is unique"""
        if Payment.objects.filter(transaction_id=value).exists():
            raise serializers.ValidationError("Transaction ID already exists")
        return value


class DeliveryConfirmationSerializer(serializers.Serializer):
    order_reference = serializers.CharField(required=True)
    delivery_code = serializers.CharField(required=True, min_length=6, max_length=6)
    
    def validate_delivery_code(self, value):
        """Validate delivery code format"""
        if not value.isdigit():
            raise serializers.ValidationError("Delivery code must be 6 digits")
        return value


class MpesaSTKPushSerializer(serializers.Serializer):
    phone_number = serializers.CharField(required=True)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=True, min_value=1)
    account_reference = serializers.CharField(required=True)
    transaction_desc = serializers.CharField(required=False, default="Payment")
    
    def validate_phone_number(self, value):
        """Validate Kenyan phone number format"""
        phone = re.sub(r'[^\d+]', '', value)
        
        if phone.startswith('+254'):
            phone = phone[1:]
        elif phone.startswith('0'):
            phone = '254' + phone[1:]
        elif not phone.startswith('254'):
            raise serializers.ValidationError("Invalid Kenyan phone number format")
        
        if len(phone) != 12:
            raise serializers.ValidationError("Phone number must be 12 digits (254XXXXXXXXX)")
        
        return phone


class PaymentSerializer(serializers.ModelSerializer):
    payer_phone_masked = serializers.SerializerMethodField()
    order_reference = serializers.CharField(source='order.order_reference', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id',
            'order_reference',
            'payment_method',
            'amount',
            'transaction_id',
            'provider_reference',
            'payer_phone_masked',
            'status',
            'metadata',
            'created_at',
            'completed_at'
        ]
        read_only_fields = ['id', 'created_at', 'completed_at']
    
    def get_payer_phone_masked(self, obj):
        """Return masked phone number"""
        if obj.payer_phone_last4:
            return f"****{obj.payer_phone_last4}"
        return None


class PayoutSerializer(serializers.ModelSerializer):
    seller_phone_masked = serializers.SerializerMethodField()
    order_reference = serializers.CharField(source='order.order_reference', read_only=True)
    
    class Meta:
        model = Payout
        fields = [
            'id',
            'order_reference',
            'amount',
            'seller_phone_masked',
            'transaction_id',
            'provider_reference',
            'status',
            'failure_reason',
            'created_at',
            'completed_at'
        ]
        read_only_fields = ['id', 'created_at', 'completed_at']
    
    def get_seller_phone_masked(self, obj):
        """Return masked phone number"""
        return f"****{obj.seller_phone_last4}"