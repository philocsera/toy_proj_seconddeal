from io import BytesIO
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


def make_image_file(name='test.jpg', fmt='JPEG', size=(100, 100)):
    buf = BytesIO()
    Image.new('RGB', size, color='red').save(buf, format=fmt)
    buf.seek(0)
    return SimpleUploadedFile(name, buf.read(), content_type='image/jpeg')


def make_user(email='user@test.com', nickname='유저', password='pass1234'):
    return User.objects.create_user(email=email, nickname=nickname, password=password)


def auth_header(client, email='user@test.com', password='pass1234'):
    resp = client.post(reverse('login'), {'email': email, 'password': password}, format='json')
    return {'HTTP_AUTHORIZATION': f'Bearer {resp.data["access"]}'}


class RegisterTest(APITestCase):
    url = reverse('register')

    def test_success(self):
        resp = self.client.post(self.url, {
            'email': 'new@test.com', 'nickname': '신규', 'password': 'x8kLm2qP!'
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIn('access', resp.data)
        self.assertIn('refresh', resp.data)
        self.assertEqual(resp.data['user']['email'], 'new@test.com')

    def test_duplicate_email(self):
        make_user()
        resp = self.client.post(self.url, {
            'email': 'user@test.com', 'nickname': '다른유저', 'password': 'pass1234'
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('이미 사용 중인 이메일', resp.data['detail'])

    def test_nickname_too_short(self):
        resp = self.client.post(self.url, {
            'email': 'short@test.com', 'nickname': 'A', 'password': 'pass1234'
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_too_short(self):
        resp = self.client.post(self.url, {
            'email': 'pw@test.com', 'nickname': '유저', 'password': '123'
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_fields(self):
        resp = self.client.post(self.url, {'email': 'only@test.com'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class LoginTest(APITestCase):
    url = reverse('login')

    def setUp(self):
        cache.clear()
        make_user()

    def test_success(self):
        resp = self.client.post(self.url, {
            'email': 'user@test.com', 'password': 'pass1234'
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('access', resp.data)
        self.assertIn('refresh', resp.data)

    def test_wrong_password(self):
        resp = self.client.post(self.url, {
            'email': 'user@test.com', 'password': 'wrongpass'
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_wrong_email(self):
        resp = self.client.post(self.url, {
            'email': 'nobody@test.com', 'password': 'pass1234'
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class MeTest(APITestCase):
    url = reverse('me')

    def setUp(self):
        cache.clear()
        make_user()

    def test_authenticated(self):
        headers = auth_header(self.client)
        resp = self.client.get(self.url, **headers)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['email'], 'user@test.com')
        self.assertEqual(resp.data['nickname'], '유저')

    def test_unauthenticated(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class TokenRefreshTest(APITestCase):
    def setUp(self):
        cache.clear()

    def test_refresh_success(self):
        make_user()
        login = self.client.post(reverse('login'), {
            'email': 'user@test.com', 'password': 'pass1234'
        }, format='json')
        resp = self.client.post(reverse('token-refresh'), {
            'refresh': login.data['refresh']
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('access', resp.data)

    def test_invalid_refresh_token(self):
        resp = self.client.post(reverse('token-refresh'), {
            'refresh': 'invalid.token.here'
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class KakaoLoginTest(APITestCase):
    url = reverse('kakao-login')

    def test_missing_code(self):
        resp = self.client.post(self.url, {}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('code가 필요합니다', resp.data['detail'])

    @patch('users.kakao._get_kakao_token', return_value='kakao_access_token')
    @patch('users.kakao._get_kakao_user_info', return_value={
        'kakao_id': '123456',
        'email': 'kakao@test.com',
        'nickname': '카카오유저',
    })
    def test_new_user_signup(self, mock_info, mock_token):
        resp = self.client.post(self.url, {'code': 'valid_code'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('access', resp.data)
        self.assertTrue(User.objects.filter(email='kakao@test.com').exists())
        self.assertEqual(User.objects.get(email='kakao@test.com').provider, 'kakao')

    @patch('users.kakao._get_kakao_token', return_value='kakao_access_token')
    @patch('users.kakao._get_kakao_user_info', return_value={
        'kakao_id': '123456',
        'email': 'user@test.com',
        'nickname': '카카오유저',
    })
    def test_existing_local_user_provider_updated(self, mock_info, mock_token):
        make_user()  # local provider
        resp = self.client.post(self.url, {'code': 'valid_code'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        user = User.objects.get(email='user@test.com')
        self.assertEqual(user.provider, 'kakao')

    @patch('users.kakao._get_kakao_token', side_effect=__import__('requests').HTTPError('401'))
    def test_kakao_api_error(self, mock_token):
        resp = self.client.post(self.url, {'code': 'bad_code'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_502_BAD_GATEWAY)


class PasswordPolicyTest(APITestCase):
    url = reverse('register')

    def test_password_min_length_8(self):
        resp = self.client.post(self.url, {
            'email': 'pw@test.com', 'nickname': '유저', 'password': 'short1'
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_numeric_only_password_rejected(self):
        resp = self.client.post(self.url, {
            'email': 'num@test.com', 'nickname': '유저', 'password': '12345678'
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class LoginRateLimitTest(APITestCase):
    """로그인 Rate Limit (5회/분) 테스트"""
    url = reverse('login')

    def setUp(self):
        cache.clear()
        make_user()

    def tearDown(self):
        cache.clear()

    def test_rate_limit_triggered_after_5_failures(self):
        for _ in range(5):
            self.client.post(self.url, {
                'email': 'user@test.com', 'password': 'wrongpass'
            }, format='json')
        resp = self.client.post(self.url, {
            'email': 'user@test.com', 'password': 'wrongpass'
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_429_TOO_MANY_REQUESTS)


class ImageUploadSecurityTest(APITestCase):
    """이미지 업로드 보안 검증"""

    def setUp(self):
        cache.clear()
        self.user = make_user()
        login = self.client.post(reverse('login'), {
            'email': 'user@test.com', 'password': 'pass1234'
        }, format='json')
        self.token = login.data['access']

    def test_valid_image_accepted(self):
        img = make_image_file('ok.jpg')
        resp = self.client.post(
            reverse('product-list-create'),
            {'title': '이미지 상품', 'description': '설명', 'price': 5000,
             'category': 'etc', 'image': img},
            format='multipart',
            HTTP_AUTHORIZATION=f'Bearer {self.token}',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_invalid_extension_rejected(self):
        # 실제 JPEG 바이트를 .php 확장자로 업로드 → ImageField PIL 검사는 통과하지만 확장자 검사에서 거부
        buf = BytesIO()
        Image.new('RGB', (10, 10), color='blue').save(buf, format='JPEG')
        evil = SimpleUploadedFile('shell.php', buf.getvalue(), content_type='image/jpeg')
        resp = self.client.post(
            reverse('product-list-create'),
            {'title': '악성 파일', 'description': '설명', 'price': 5000,
             'category': 'etc', 'image': evil},
            format='multipart',
            HTTP_AUTHORIZATION=f'Bearer {self.token}',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('php', resp.data['detail'])

    def test_oversized_image_rejected(self):
        # BMP 비압축 포맷(1500x1500 ≈ 6.75MB)을 .jpg 확장자로 업로드
        # PIL은 파일 시그니처로 포맷을 판별하므로 DRF ImageField 검증은 통과,
        # 이후 validate_image_file의 크기 검사에서 거부
        buf = BytesIO()
        Image.new('RGB', (1500, 1500), color='green').save(buf, format='BMP')
        large = SimpleUploadedFile('big.jpg', buf.getvalue(), content_type='image/jpeg')
        resp = self.client.post(
            reverse('product-list-create'),
            {'title': '큰 파일', 'description': '설명', 'price': 5000,
             'category': 'etc', 'image': large},
            format='multipart',
            HTTP_AUTHORIZATION=f'Bearer {self.token}',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('5MB', resp.data['detail'])
