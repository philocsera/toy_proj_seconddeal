import uuid

from rest_framework import serializers

from products.models import Product
from .models import Order


class OrderCreateSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()

    def validate_product_id(self, value):
        try:
            product = Product.objects.get(pk=value, status=Product.Status.ON_SALE)
        except Product.DoesNotExist:
            raise serializers.ValidationError('판매중인 상품이 아닙니다.')
        return value

    def create(self, validated_data):
        product = Product.objects.get(pk=validated_data['product_id'])
        buyer = self.context['request'].user
        merchant_uid = f'order_{uuid.uuid4().hex}'
        order = Order.objects.create(
            buyer=buyer,
            product=product,
            total_price=product.price,
            merchant_uid=merchant_uid,
        )
        product.status = Product.Status.RESERVED
        product.save(update_fields=['status'])
        return order


class OrderSerializer(serializers.ModelSerializer):
    product_title = serializers.CharField(source='product.title', read_only=True)
    product_price = serializers.IntegerField(source='product.price', read_only=True)
    buyer_nickname = serializers.CharField(source='buyer.nickname', read_only=True)

    class Meta:
        model = Order
        fields = (
            'id', 'buyer_nickname', 'product_title', 'product_price',
            'status', 'total_price', 'merchant_uid', 'created_at',
        )
