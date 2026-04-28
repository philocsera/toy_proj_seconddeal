import os
from rest_framework import serializers

ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
MAX_IMAGE_SIZE_MB = 5
MAX_IMAGE_BYTES = MAX_IMAGE_SIZE_MB * 1024 * 1024


def validate_image_file(image):
    """이미지 확장자와 크기를 검증한다."""
    ext = os.path.splitext(image.name)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise serializers.ValidationError(
            f'지원하지 않는 파일 형식입니다. ({", ".join(ALLOWED_IMAGE_EXTENSIONS)}만 허용)'
        )
    if image.size > MAX_IMAGE_BYTES:
        raise serializers.ValidationError(
            f'이미지 크기는 {MAX_IMAGE_SIZE_MB}MB 이하여야 합니다.'
        )
    return image
