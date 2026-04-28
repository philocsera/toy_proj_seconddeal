import requests
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

from .serializers import TokenResponseSerializer

User = get_user_model()

KAKAO_TOKEN_URL = 'https://kauth.kakao.com/oauth/token'
KAKAO_USERINFO_URL = 'https://kapi.kakao.com/v2/user/me'


def _get_kakao_token(code: str) -> str:
    """인가코드를 카카오 액세스 토큰으로 교환"""
    resp = requests.post(KAKAO_TOKEN_URL, data={
        'grant_type': 'authorization_code',
        'client_id': settings.KAKAO_CLIENT_ID,
        'redirect_uri': settings.KAKAO_REDIRECT_URI,
        'code': code,
    }, timeout=10)
    resp.raise_for_status()
    return resp.json()['access_token']


def _get_kakao_user_info(access_token: str) -> dict:
    """카카오 액세스 토큰으로 사용자 정보 조회"""
    resp = requests.get(KAKAO_USERINFO_URL, headers={
        'Authorization': f'Bearer {access_token}',
    }, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    kakao_account = data.get('kakao_account', {})
    profile = kakao_account.get('profile', {})
    return {
        'kakao_id': str(data['id']),
        'email': kakao_account.get('email', f"kakao_{data['id']}@kakao.local"),
        'nickname': profile.get('nickname', f"kakao_{data['id']}"),
    }


def _upsert_kakao_user(info: dict) -> User:
    """카카오 유저를 users 테이블에 upsert.
    같은 이메일로 로컬 계정이 이미 존재하면 provider를 kakao로 업데이트.
    """
    user, created = User.objects.get_or_create(
        email=info['email'],
        defaults={
            'nickname': info['nickname'],
            'provider': User.Provider.KAKAO,
        },
    )
    if not created and user.provider == User.Provider.LOCAL:
        user.provider = User.Provider.KAKAO
        user.save(update_fields=['provider'])
    return user


class KakaoLoginView(APIView):
    """
    프론트에서 카카오 인가코드를 받아 JWT를 발급한다.

    POST /api/auth/kakao/
    Body: { "code": "<카카오 인가코드>" }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        code = request.data.get('code')
        if not code:
            return Response({'detail': 'code가 필요합니다.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            access_token = _get_kakao_token(code)
            user_info = _get_kakao_user_info(access_token)
        except requests.HTTPError as e:
            return Response({'detail': f'카카오 API 오류: {e}'}, status=status.HTTP_502_BAD_GATEWAY)

        user = _upsert_kakao_user(user_info)
        return Response(TokenResponseSerializer.for_user(user))
