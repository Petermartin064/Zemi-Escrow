from django.contrib import admin

from .models import Order, Payment, Payout, WebhookLog

admin.site.register(Order)
admin.site.register(Payment)
admin.site.register(Payout)
admin.site.register(WebhookLog)