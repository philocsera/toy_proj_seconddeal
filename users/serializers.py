from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from rest_framework_simplejwt.tokens import RefreshToken

from config.validators import validate_image_file

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    email = serializers.EmailField(
        validators=[UniqueValidator(queryset=User.objects.all(), message='이미 사용 중인 이메일입니다.')]
    )

    class Meta:
        model = User
        fields = ('email', 'nickname', 'password')

    def validate_nickname(self, value):
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError('닉네임은 2자 이상이어야 합니다.')
        if len(value) > 20:
            raise serializers.ValidationError('닉네임은 20자 이하여야 합니다.')
        return value

    def validate_password(self, value):
        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.messages)
        return value

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'nickname', 'profile_image', 'provider', 'created_at')


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('nickname', 'profile_image')

    def validate_nickname(self, value):
        value = value.strip()
        if len(value) < 2:
            raise serializers.ValidationError('닉네임은 2자 이상이어야 합니다.')
        if len(value) > 20:
            raise serializers.ValidationError('닉네임은 20자 이하여야 합니다.')
        return value

    def validate_profile_image(self, value):
        if value:
            return validate_image_file(value)
        return value


class TokenResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserSerializer()

    @staticmethod
    def for_user(user):
        refresh = RefreshToken.for_user(user)
        return {
            'access': str(refresh.access_token),
            'refresh': str(refresh),
            'user': UserSerializer(user).data,
        }
