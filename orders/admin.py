from django.contrib import admin

from .models import Order


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'buyer', 'product', 'status', 'total_price', 'created_at')
    list_filter = ('status',)
    search_fields = ('merchant_uid', 'buyer__email')
