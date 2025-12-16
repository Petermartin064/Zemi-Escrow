from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db import transaction
from django.contrib.auth.hashers import check_password
from django.utils import timezone
from .models import Order, Payment, Payout, WebhookLog
from .serializers import (
    CreateOrderSerializer, OrderSerializer, PaymentWebhookSerializer,
    DeliveryConfirmationSerializer, MpesaSTKPushSerializer,
    PaymentSerializer, PayoutSerializer
)
from .services.mpesa_service import MpesaService
import logging

logger = logging.getLogger(__name__)


@api_view(['POST'])
def create_order(request):
    """
    Create a new buyer-initiated order
    
    POST /api/orders/create
    {
        "buyer_phone": "254712345678",
        "amount": 1500.00,
        "product_description": "iPhone 13 Pro Max 256GB"
    }
    """
    serializer = CreateOrderSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    validated_data = serializer.validated_data
    
    try:
        with transaction.atomic():
            # Generate order reference and delivery code
            order_reference = Order.generate_order_reference()
            delivery_code = Order.generate_delivery_code()
            
            # Hash sensitive data
            phone_hash = Order.hash_phone_number(validated_data['buyer_phone'])
            phone_last4 = Order.get_last_4_digits(validated_data['buyer_phone'])
            code_hash = Order.hash_phone_number(delivery_code)  # Reuse hash function
            
            # Create order
            order = Order.objects.create(
                order_reference=order_reference,
                buyer_phone_hash=phone_hash,
                buyer_phone_last4=phone_last4,
                amount=validated_data['amount'],
                product_description=validated_data['product_description'],
                delivery_code_hash=code_hash,
                status='awaiting_payment'
            )
            
            logger.info(f"Order created: {order_reference}")
            
            return Response({
                'success': True,
                'data': {
                    'order_reference': order.order_reference,
                    'amount': str(order.amount),
                    'status': order.status,
                    'delivery_code': delivery_code,  # Return unhashed code to buyer
                    'created_at': order.created_at.isoformat(),
                    'message': 'Order created successfully. Keep your delivery code safe!'
                }
            }, status=status.HTTP_201_CREATED)
            
    except Exception as e:
        logger.error(f"Order creation failed: {str(e)}")
        return Response({
            'success': False,
            'error': 'Failed to create order'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def payment_webhook(request):
    """
    Simulated payment confirmation webhook
    This endpoint is SEPARATE from order creation and can only mark orders as paid
    
    POST /api/webhooks/payment
    {
        "order_reference": "ZEM-ABC123",
        "transaction_id": "TXN123456789",
        "amount": 1500.00,
        "payment_method": "mpesa",
        "payer_phone": "254712345678",
        "metadata": {}
    }
    """
    serializer = PaymentWebhookSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    validated_data = serializer.validated_data
    
    try:
        with transaction.atomic():
            # Find the order
            try:
                order = Order.objects.select_for_update().get(
                    order_reference=validated_data['order_reference']
                )
            except Order.DoesNotExist:
                return Response({
                    'success': False,
                    'error': 'Order not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Validate order can be paid
            if not order.can_transition_to('paid'):
                return Response({
                    'success': False,
                    'error': f'Order cannot be paid. Current status: {order.status}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate amount matches
            if order.amount != validated_data['amount']:
                return Response({
                    'success': False,
                    'error': 'Payment amount does not match order amount'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Hash payer phone if provided
            payer_phone_hash = None
            payer_phone_last4 = None
            if validated_data.get('payer_phone'):
                payer_phone_hash = Order.hash_phone_number(validated_data['payer_phone'])
                payer_phone_last4 = Order.get_last_4_digits(validated_data['payer_phone'])
            
            # Create payment record
            payment = Payment.objects.create(
                order=order,
                payment_method=validated_data['payment_method'],
                amount=validated_data['amount'],
                transaction_id=validated_data['transaction_id'],
                payer_phone_hash=payer_phone_hash,
                payer_phone_last4=payer_phone_last4,
                metadata=validated_data.get('metadata', {}),
                status='completed'
            )
            
            # Update order status
            order.status = 'paid'
            order.paid_at = timezone.now()
            order.save()
            
            payment.completed_at = timezone.now()
            payment.save()
            
            logger.info(f"Payment confirmed for order {order.order_reference}")
            
            return Response({
                'success': True,
                'data': {
                    'order_reference': order.order_reference,
                    'transaction_id': payment.transaction_id,
                    'status': order.status,
                    'paid_at': order.paid_at.isoformat()
                }
            }, status=status.HTTP_200_OK)
            
    except Exception as e:
        logger.error(f"Payment webhook processing failed: {str(e)}")
        return Response({
            'success': False,
            'error': 'Failed to process payment'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def confirm_delivery(request):
    """
    Buyer confirms delivery using delivery code
    
    POST /api/orders/confirm-delivery
    {
        "order_reference": "ZEM-ABC123",
        "delivery_code": "123456"
    }
    """
    serializer = DeliveryConfirmationSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    validated_data = serializer.validated_data
    
    try:
        with transaction.atomic():
            # Find the order
            try:
                order = Order.objects.select_for_update().get(
                    order_reference=validated_data['order_reference']
                )
            except Order.DoesNotExist:
                return Response({
                    'success': False,
                    'error': 'Order not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Validate order status
            if not order.can_transition_to('completed'):
                return Response({
                    'success': False,
                    'error': f'Order cannot be completed. Current status: {order.status}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Verify delivery code
            if not check_password(validated_data['delivery_code'], order.delivery_code_hash):
                return Response({
                    'success': False,
                    'error': 'Invalid delivery code'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get the payment for this order
            try:
                payment = Payment.objects.get(order=order, status='completed')
            except Payment.DoesNotExist:
                return Response({
                    'success': False,
                    'error': 'No completed payment found for this order'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Simulate releasing funds to seller (create payout record)
            # In production, this would trigger actual B2C payment
            payout = Payout.objects.create(
                order=order,
                payment=payment,
                amount=order.amount,
                seller_phone_hash=order.buyer_phone_hash,  # Simulate seller phone
                seller_phone_last4=order.buyer_phone_last4,
                status='pending',
                metadata={'simulated': True}
            )
            
            # Update order status
            order.status = 'completed'
            order.completed_at = timezone.now()
            order.save()
            
            logger.info(f"Delivery confirmed for order {order.order_reference}")
            
            return Response({
                'success': True,
                'data': {
                    'order_reference': order.order_reference,
                    'status': order.status,
                    'completed_at': order.completed_at.isoformat(),
                    'payout_initiated': True,
                    'message': 'Delivery confirmed. Payment is being released to seller.'
                }
            }, status=status.HTTP_200_OK)
            
    except Exception as e:
        logger.error(f"Delivery confirmation failed: {str(e)}")
        return Response({
            'success': False,
            'error': 'Failed to confirm delivery'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def mpesa_stk_push(request):
    """
    Initiate M-Pesa STK Push for payment collection
    
    POST /api/payments/mpesa/stk-push
    {
        "phone_number": "254712345678",
        "amount": 1500.00,
        "account_reference": "ZEM-ABC123",
        "transaction_desc": "Payment for order"
    }
    """
    serializer = MpesaSTKPushSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    validated_data = serializer.validated_data
    
    try:
        mpesa_service = MpesaService()
        result = mpesa_service.stk_push(
            phone_number=validated_data['phone_number'],
            amount=validated_data['amount'],
            account_reference=validated_data['account_reference'],
            transaction_desc=validated_data.get('transaction_desc', 'Payment')
        )
        
        if result['success']:
            return Response({
                'success': True,
                'data': result
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'error': result.get('error', 'STK Push failed')
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"STK Push failed: {str(e)}")
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def mpesa_callback(request):
    """
    M-Pesa STK Push callback endpoint
    
    This receives payment notifications from M-Pesa Daraja API
    """
    try:
        # Log the webhook
        webhook_log = WebhookLog.objects.create(
            webhook_type='mpesa_stk',
            payload=request.data,
            headers=dict(request.headers)
        )
        
        # Process the callback
        body = request.data.get('Body', {})
        stk_callback = body.get('stkCallback', {})
        
        result_code = stk_callback.get('ResultCode')
        checkout_request_id = stk_callback.get('CheckoutRequestID')
        
        if result_code == 0:
            # Payment successful
            callback_metadata = stk_callback.get('CallbackMetadata', {})
            items = callback_metadata.get('Item', [])
            
            # Extract payment details
            amount = None
            mpesa_receipt = None
            phone_number = None
            
            for item in items:
                name = item.get('Name')
                value = item.get('Value')
                
                if name == 'Amount':
                    amount = value
                elif name == 'MpesaReceiptNumber':
                    mpesa_receipt = value
                elif name == 'PhoneNumber':
                    phone_number = value
            
            webhook_log.transaction_id = mpesa_receipt
            webhook_log.processed = True
            webhook_log.save()
            
            logger.info(f"M-Pesa payment successful: {mpesa_receipt}")
            
        else:
            # Payment failed
            result_desc = stk_callback.get('ResultDesc')
            webhook_log.processing_error = result_desc
            webhook_log.processed = True
            webhook_log.save()
            
            logger.warning(f"M-Pesa payment failed: {result_desc}")
        
        return Response({'ResultCode': 0, 'ResultDesc': 'Success'})
        
    except Exception as e:
        logger.error(f"M-Pesa callback processing failed: {str(e)}")
        return Response({'ResultCode': 1, 'ResultDesc': 'Failed'})


@api_view(['GET'])
def get_order(request, order_reference):
    """Get order details"""
    try:
        order = Order.objects.get(order_reference=order_reference)
        serializer = OrderSerializer(order)
        return Response({
            'success': True,
            'data': serializer.data
        })
    except Order.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Order not found'
        }, status=status.HTTP_404_NOT_FOUND)