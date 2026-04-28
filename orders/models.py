from django.conf import settings
from django.db import models

from products.models import Product


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', '결제대기'
        PAID = 'paid', '결제완료'
        CANCELLED = 'cancelled', '취소됨'

    buyer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='orders',
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name='orders',
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    total_price = models.PositiveIntegerField()
    merchant_uid = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'orders'
        ordering = ['-created_at']

    def __str__(self):
        return f'Order #{self.pk} - {self.product.title}'
