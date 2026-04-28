from rest_framework import serializers

from .models import Product


class ProductSerializer(serializers.ModelSerializer):
    seller_nickname = serializers.CharField(source='seller.nickname', read_only=True)

    class Meta:
        model = Product
        fields = (
            'id', 'seller', 'seller_nickname',
            'title', 'description', 'price',
            'category', 'status', 'image',
            'created_at', 'updated_at',
        )
        read_only_fields = ('seller', 'status', 'created_at', 'updated_at')


class ProductCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ('title', 'description', 'price', 'category', 'image')

    def create(self, validated_data):
        validated_data['seller'] = self.context['request'].user
        return super().create(validated_data)


class ProductStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ('status',)
