from django.contrib import admin

from .models import Product


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('title', 'seller', 'price', 'category', 'status', 'created_at')
    list_filter = ('category', 'status')
    search_fields = ('title', 'description')
    ordering = ('-created_at',)
