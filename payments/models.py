from django.db import models

from orders.models import Order


class Payment(models.Model):
    class Status(models.TextChoices):
        READY = 'ready', '결제준비'
        PAID = 'paid', '결제완료'
        CANCELLED = 'cancelled', '취소됨'
        FAILED = 'failed', '실패'

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    imp_uid = models.CharField(max_length=100, unique=True)
    merchant_uid = models.CharField(max_length=100)
    amount = models.PositiveIntegerField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.READY)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'payments'

    def __str__(self):
        return f'Payment {self.imp_uid} - {self.status}'
