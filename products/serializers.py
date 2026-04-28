from rest_framework import serializers

from config.validators import validate_image_file
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

    def validate_price(self, value):
        if value < 100:
            raise serializers.ValidationError('가격은 100원 이상이어야 합니다.')
        if value > 100_000_000:
            raise serializers.ValidationError('가격은 1억원을 초과할 수 없습니다.')
        return value

    def validate_title(self, value):
        if len(value.strip()) < 2:
            raise serializers.ValidationError('제목은 2자 이상이어야 합니다.')
        return value.strip()

    def validate_image(self, value):
        if value:
            return validate_image_file(value)
        return value

    def create(self, validated_data):
        validated_data['seller'] = self.context['request'].user
        return super().create(validated_data)


class ProductStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ('status',)
