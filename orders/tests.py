from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from products.models import Product
from .models import Order

User = get_user_model()


def make_user(email='buyer@test.com', nickname='구매자', password='pass1234'):
    return User.objects.create_user(email=email, nickname=nickname, password=password)


def get_token(client, email, password='pass1234'):
    resp = client.post(reverse('login'), {'email': email, 'password': password}, format='json')
    return resp.data['access']


def auth(token):
    return {'HTTP_AUTHORIZATION': f'Bearer {token}'}


def make_product(seller, status='on_sale', price=10000):
    return Product.objects.create(
        seller=seller, title='테스트 상품', description='설명',
        price=price, category='etc', status=status,
    )


class OrderCreateTest(APITestCase):
    url = reverse('order-create')

    def setUp(self):
        self.seller = make_user(email='seller@test.com', nickname='판매자')
        self.buyer = make_user()
        self.product = make_product(self.seller)
        self.token = get_token(self.client, 'buyer@test.com')

    def test_create_success(self):
        resp = self.client.post(self.url, {'product_id': self.product.pk}, format='json', **auth(self.token))
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data['status'], 'pending')
        self.assertEqual(resp.data['total_price'], self.product.price)
        self.assertIn('merchant_uid', resp.data)

    def test_product_status_changes_to_reserved(self):
        self.client.post(self.url, {'product_id': self.product.pk}, format='json', **auth(self.token))
        self.product.refresh_from_db()
        self.assertEqual(self.product.status, 'reserved')

    def test_order_not_on_sale_product(self):
        sold_product = make_product(self.seller, status='sold')
        resp = self.client.post(self.url, {'product_id': sold_product.pk}, format='json', **auth(self.token))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('판매중인 상품이 아닙니다', resp.data['detail'])

    def test_order_reserved_product(self):
        reserved_product = make_product(self.seller, status='reserved')
        resp = self.client.post(self.url, {'product_id': reserved_product.pk}, format='json', **auth(self.token))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_order_nonexistent_product(self):
        resp = self.client.post(self.url, {'product_id': 99999}, format='json', **auth(self.token))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated(self):
        resp = self.client.post(self.url, {'product_id': self.product.pk}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_merchant_uid_is_unique(self):
        # 두 번 주문해도 merchant_uid가 달라야 한다
        p1 = make_product(self.seller)
        p2 = make_product(self.seller)
        r1 = self.client.post(self.url, {'product_id': p1.pk}, format='json', **auth(self.token))
        r2 = self.client.post(self.url, {'product_id': p2.pk}, format='json', **auth(self.token))
        self.assertNotEqual(r1.data['merchant_uid'], r2.data['merchant_uid'])


class MyOrderListTest(APITestCase):
    url = reverse('my-orders')

    def setUp(self):
        self.seller = make_user(email='seller@test.com', nickname='판매자')
        self.buyer1 = make_user()
        self.buyer2 = make_user(email='buyer2@test.com', nickname='구매자2')
        self.token1 = get_token(self.client, 'buyer@test.com')
        self.token2 = get_token(self.client, 'buyer2@test.com')

        p1 = make_product(self.seller)
        p2 = make_product(self.seller)
        p3 = make_product(self.seller)
        Order.objects.create(buyer=self.buyer1, product=p1, total_price=p1.price, merchant_uid='uid1')
        Order.objects.create(buyer=self.buyer1, product=p2, total_price=p2.price, merchant_uid='uid2')
        Order.objects.create(buyer=self.buyer2, product=p3, total_price=p3.price, merchant_uid='uid3')

    def test_returns_only_my_orders(self):
        resp = self.client.get(self.url, **auth(self.token1))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 2)

    def test_other_buyer_sees_own_orders(self):
        resp = self.client.get(self.url, **auth(self.token2))
        self.assertEqual(len(resp.data), 1)

    def test_unauthenticated(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
