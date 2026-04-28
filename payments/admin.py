from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('imp_uid', 'order', 'amount', 'status', 'paid_at')
    list_filter = ('status',)
    search_fields = ('imp_uid', 'merchant_uid')
