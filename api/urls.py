from django.urls import path
from . import views

urlpatterns = [
    # Order endpoints
    path('orders/create/', views.create_order, name='create_order'),
    path('orders/confirm-delivery/', views.confirm_delivery, name='confirm_delivery'),
    path('orders/<str:order_reference>/', views.get_order, name='get_order'),
    
    
    # Payment endpoints
    path('payments/mpesa/stk-push/', views.mpesa_stk_push, name='mpesa_stk_push'),
    
    # Webhook endpoints for payment notifications
    path('webhooks/payment/', views.payment_webhook, name='payment_webhook'),
    path('webhooks/mpesa/', views.mpesa_callback, name='mpesa_callback'),
]