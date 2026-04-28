from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Product

User = get_user_model()


def make_user(email='seller@test.com', nickname='판매자', password='pass1234'):
    return User.objects.create_user(email=email, nickname=nickname, password=password)


def get_token(client, email, password='pass1234'):
    resp = client.post(reverse('login'), {'email': email, 'password': password}, format='json')
    return resp.data['access']


def auth(token):
    return {'HTTP_AUTHORIZATION': f'Bearer {token}'}


def make_product(seller, **kwargs):
    defaults = dict(title='테스트 상품', description='설명', price=10000, category='etc')
    defaults.update(kwargs)
    return Product.objects.create(seller=seller, **defaults)


class ProductListTest(APITestCase):
    url = reverse('product-list-create')

    def setUp(self):
        self.seller = make_user()
        make_product(self.seller, title='맥북 프로', category='electronics', status='on_sale')
        make_product(self.seller, title='나이키 신발', category='fashion', status='sold')

    def test_list_no_auth(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 2)

    def test_keyword_filter(self):
        resp = self.client.get(self.url, {'q': '맥북'})
        self.assertEqual(len(resp.data), 1)
        self.assertIn('맥북', resp.data[0]['title'])

    def test_category_filter(self):
        resp = self.client.get(self.url, {'category': 'fashion'})
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]['category'], 'fashion')

    def test_status_filter(self):
        resp = self.client.get(self.url, {'status': 'sold'})
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]['status'], 'sold')


class ProductCreateTest(APITestCase):
    url = reverse('product-list-create')

    def setUp(self):
        cache.clear()
        self.seller = make_user()
        self.token = get_token(self.client, 'seller@test.com')

    def test_create_success(self):
        resp = self.client.post(self.url, {
            'title': '새 상품', 'description': '설명', 'price': 5000, 'category': 'book'
        }, format='json', **auth(self.token))
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['title'], '새 상품')
        self.assertEqual(resp.data['status'], 'on_sale')

    def test_create_unauthenticated(self):
        resp = self.client.post(self.url, {
            'title': '상품', 'description': '설명', 'price': 5000, 'category': 'etc'
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_price_too_low(self):
        resp = self.client.post(self.url, {
            'title': '상품', 'description': '설명', 'price': 50, 'category': 'etc'
        }, format='json', **auth(self.token))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('100원', resp.data['detail'])

    def test_price_too_high(self):
        resp = self.client.post(self.url, {
            'title': '상품', 'description': '설명', 'price': 200_000_000, 'category': 'etc'
        }, format='json', **auth(self.token))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_title_too_short(self):
        resp = self.client.post(self.url, {
            'title': 'A', 'description': '설명', 'price': 5000, 'category': 'etc'
        }, format='json', **auth(self.token))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class ProductDetailTest(APITestCase):
    def setUp(self):
        cache.clear()
        self.seller = make_user()
        self.other = make_user(email='other@test.com', nickname='타인')
        self.product = make_product(self.seller)
        self.seller_token = get_token(self.client, 'seller@test.com')
        self.other_token = get_token(self.client, 'other@test.com')
        self.url = reverse('product-detail', kwargs={'pk': self.product.pk})

    def test_retrieve_no_auth(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['title'], self.product.title)

    def test_update_by_owner(self):
        resp = self.client.put(self.url, {
            'title': '수정된 제목', 'description': '수정 설명', 'price': 20000, 'category': 'etc'
        }, format='json', **auth(self.seller_token))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['title'], '수정된 제목')

    def test_update_by_non_owner(self):
        resp = self.client.put(self.url, {
            'title': '무단 수정', 'description': '설명', 'price': 20000, 'category': 'etc'
        }, format='json', **auth(self.other_token))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_by_owner(self):
        resp = self.client.delete(self.url, **auth(self.seller_token))
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Product.objects.filter(pk=self.product.pk).exists())

    def test_delete_by_non_owner(self):
        resp = self.client.delete(self.url, **auth(self.other_token))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_not_found(self):
        resp = self.client.get(reverse('product-detail', kwargs={'pk': 99999}))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


class ProductStatusTest(APITestCase):
    def setUp(self):
        cache.clear()
        self.seller = make_user()
        self.other = make_user(email='other@test.com', nickname='타인')
        self.product = make_product(self.seller)
        self.seller_token = get_token(self.client, 'seller@test.com')
        self.other_token = get_token(self.client, 'other@test.com')
        self.url = reverse('product-status', kwargs={'pk': self.product.pk})

    def test_status_change_by_owner(self):
        resp = self.client.patch(self.url, {'status': 'reserved'}, format='json', **auth(self.seller_token))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.product.refresh_from_db()
        self.assertEqual(self.product.status, 'reserved')

    def test_status_change_by_non_owner(self):
        resp = self.client.patch(self.url, {'status': 'reserved'}, format='json', **auth(self.other_token))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_status_change_unauthenticated(self):
        resp = self.client.patch(self.url, {'status': 'reserved'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


class MyProductListTest(APITestCase):
    url = reverse('my-products')

    def setUp(self):
        cache.clear()
        self.seller = make_user()
        self.other = make_user(email='other@test.com', nickname='타인')
        make_product(self.seller, title='내 상품 1')
        make_product(self.seller, title='내 상품 2')
        make_product(self.other, title='타인 상품')
        self.token = get_token(self.client, 'seller@test.com')

    def test_only_my_products_returned(self):
        resp = self.client.get(self.url, **auth(self.token))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 2)
        titles = [p['title'] for p in resp.data]
        self.assertNotIn('타인 상품', titles)

    def test_unauthenticated(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
