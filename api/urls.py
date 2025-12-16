from django.urls import path
from . import views

urlpatterns = [
    # Order endpoints
    path('orders/create/', views.create_order, name='create_order'),
    path('orders/confirm-delivery/', views.confirm_delivery, name='confirm_delivery'),
    path('orders/<str:order_reference>/', views.get_order, name='get_order'),
    
    
    # Payment endpoints
    path('payments/mpesa/stk-push/', views.mpesa_stk_push, name='mpesa_stk_push'),
    path('payments/mpesa/b2c-payout/', views.mpesa_b2c_payout, name='mpesa_b2c_payout'),
    
    # Webhook endpoints for payment notifications
    path('webhooks/payment/', views.payment_webhook, name='payment_webhook'),
    path('webhooks/mpesa/', views.mpesa_callback, name='mpesa_callback'),
    path('webhooks/mpesa-b2c-result/', views.mpesa_b2c_result, name='mpesa_b2c_result'),
    path('webhooks/mpesa-b2c-timeout/', views.mpesa_b2c_timeout, name='mpesa_b2c_timeout'),
]