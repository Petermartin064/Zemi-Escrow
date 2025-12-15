from django.db import models
from django.contrib.auth.hashers import make_password
import uuid
import random
import string
from decimal import Decimal

class Order(models.Model):
    STATUS_CHOICES = [
        ('awaiting_payment', 'Awaiting Payment'),
        ('paid', 'Paid'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_reference = models.CharField(max_length=20, unique=True, db_index=True)
    
    # Buyer information (hashed for security)
    buyer_phone_hash = models.CharField(max_length=255)
    buyer_phone_last4 = models.CharField(max_length=4)  # For display purposes
    
    # Order details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    product_description = models.TextField()
    
    # Delivery code (hashed for security)
    delivery_code_hash = models.CharField(max_length=255)
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='awaiting_payment')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'orders'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['order_reference']),
        ]
    
    def __str__(self):
        return f"Order {self.order_reference} - {self.status}"
    
    @staticmethod
    def generate_order_reference():
        """Generate unique order reference like ZEM-ABC123"""
        timestamp = uuid.uuid4().hex[:6].upper()
        return f"ZEM-{timestamp}"
    
    @staticmethod
    def generate_delivery_code():
        """Generate 6-digit delivery code"""
        return ''.join(random.choices(string.digits, k=6))
    
    @staticmethod
    def hash_phone_number(phone: str) -> str:
        """Hash phone number for security"""
        return make_password(phone)
    
    @staticmethod
    def get_last_4_digits(phone: str) -> str:
        """Get last 4 digits of phone for display"""
        return phone[-4:] if len(phone) >= 4 else phone
    
    def can_transition_to(self, new_status: str) -> bool:
        """Validate order state transitions"""
        valid_transitions = {
            'awaiting_payment': ['paid', 'cancelled'],
            'paid': ['completed', 'refunded', 'cancelled'],
            'completed': [],
            'cancelled': [],
            'refunded': [],
        }
        return new_status in valid_transitions.get(self.status, [])


class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('mpesa', 'M-Pesa'),
        ('stripe', 'Stripe'),
        ('visa', 'Visa'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payments')
    
    # Payment details
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Transaction tracking
    transaction_id = models.CharField(max_length=255, unique=True, db_index=True)
    provider_reference = models.CharField(max_length=255, null=True, blank=True)
    
    # Phone number (hashed)
    payer_phone_hash = models.CharField(max_length=255, null=True, blank=True)
    payer_phone_last4 = models.CharField(max_length=4, null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'payments'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['transaction_id']),
            models.Index(fields=['status', 'created_at']),
        ]
    
    def __str__(self):
        return f"Payment {self.transaction_id} - {self.status}"


class Payout(models.Model):
    PAYOUT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='payouts')
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='payouts')
    
    # Payout details
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Seller information (hashed)
    seller_phone_hash = models.CharField(max_length=255)
    seller_phone_last4 = models.CharField(max_length=4)
    
    # Transaction tracking
    transaction_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    provider_reference = models.CharField(max_length=255, null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=PAYOUT_STATUS_CHOICES, default='pending')
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    failure_reason = models.TextField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'payouts'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Payout {self.transaction_id} - {self.status}"


class WebhookLog(models.Model):
    """Log all webhook requests for debugging and audit"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    webhook_type = models.CharField(max_length=50)  # mpesa_stk, mpesa_b2c, stripe, etc.
    payload = models.JSONField()
    headers = models.JSONField(default=dict)
    
    # Processing
    processed = models.BooleanField(default=False)
    processing_error = models.TextField(null=True, blank=True)
    
    # Related records
    order_reference = models.CharField(max_length=20, null=True, blank=True)
    transaction_id = models.CharField(max_length=255, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'webhook_logs'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Webhook {self.webhook_type} - {self.created_at}"