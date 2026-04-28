from django.conf import settings
from django.db import models


class Product(models.Model):
    class Status(models.TextChoices):
        ON_SALE = 'on_sale', '판매중'
        RESERVED = 'reserved', '예약중'
        SOLD = 'sold', '판매완료'

    class Category(models.TextChoices):
        ELECTRONICS = 'electronics', '전자기기'
        FASHION = 'fashion', '패션'
        BOOK = 'book', '도서'
        SPORTS = 'sports', '스포츠'
        ETC = 'etc', '기타'

    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='products',
    )
    title = models.CharField(max_length=100)
    description = models.TextField()
    price = models.PositiveIntegerField()
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.ETC)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ON_SALE)
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'products'
        ordering = ['-created_at']

    def __str__(self):
        return self.title
