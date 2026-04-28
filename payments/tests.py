from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from orders.models import Order
from products.models import Product
from .models import Payment

User = get_user_model()

VERIFY_URL = reverse('payment-verify')
CANCEL_URL = reverse('payment-cancel')
CHECKOUT_URL = reverse('checkout')


def make_user(email='buyer@test.com', nickname='구매자', password='pass1234'):
    return User.objects.create_user(email=email, nickname=nickname, password=password)


def get_token(client, email, password='pass1234'):
    resp = client.post(reverse('login'), {'email': email, 'password': password}, format='json')
    return resp.data['access']


def auth(token):
    return {'HTTP_AUTHORIZATION': f'Bearer {token}'}


def make_pending_order(buyer, price=10000):
    seller = User.objects.create_user(email='seller_p@test.com', nickname='판매자', password='pass1234')
    product = Product.objects.create(
        seller=seller, title='결제 상품', description='설명',
        price=price, category='etc', status='reserved',
    )
    return Order.objects.create(
        buyer=buyer, product=product,
        total_price=price, merchant_uid='test_merchant_uid',
    )


def make_paid_order(buyer, price=10000):
    order = make_pending_order(buyer, price)
    order.status = Order.Status.PAID
    order.save()
    Payment.objects.create(
        order=order, imp_uid='imp_test_uid',
        merchant_uid=order.merchant_uid,
        amount=price, status=Payment.Status.PAID,
        paid_at=timezone.now(),
    )
    return order


class CheckoutPageTest(APITestCase):
    def test_checkout_page_returns_200(self):
        resp = self.client.get(CHECKOUT_URL)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertContains(resp, 'PortOne')
        self.assertContains(resp, 'IMP.request_pay')


class PaymentVerifyTest(APITestCase):
    def setUp(self):
        self.buyer = make_user()
        self.token = get_token(self.client, 'buyer@test.com')
        self.order = make_pending_order(self.buyer, price=10000)

    def _post(self, data):
        return self.client.post(VERIFY_URL, data, format='json', **auth(self.token))

    def test_missing_params(self):
        resp = self._post({})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('imp_uid', resp.data['detail'])

    def test_order_not_found(self):
        resp = self._post({'imp_uid': 'imp_x', 'merchant_uid': 'wrong_uid'})
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    @patch('payments.views.fetch_payment', return_value={'amount': 10000, 'status': 'paid'})
    def test_verify_success(self, mock_fetch):
        resp = self._post({'imp_uid': 'imp_ok', 'merchant_uid': 'test_merchant_uid'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('결제 검증 완료', resp.data['detail'])

        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.PAID)
        self.order.product.refresh_from_db()
        self.assertEqual(self.order.product.status, 'sold')
        self.assertTrue(Payment.objects.filter(order=self.order).exists())

    @patch('payments.views.fetch_payment', return_value={'amount': 1000, 'status': 'paid'})
    def test_amount_mismatch(self, mock_fetch):
        # PortOne 실제 금액(1000) ≠ 주문 금액(10000) → 위변조 감지
        resp = self._post({'imp_uid': 'imp_tamper', 'merchant_uid': 'test_merchant_uid'})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('불일치', resp.data['detail'])

    @patch('payments.views.fetch_payment', return_value={'amount': 10000, 'status': 'ready'})
    def test_payment_status_not_paid(self, mock_fetch):
        resp = self._post({'imp_uid': 'imp_ready', 'merchant_uid': 'test_merchant_uid'})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('결제 상태 이상', resp.data['detail'])

    @patch('payments.views.fetch_payment', return_value={'amount': 10000, 'status': 'paid'})
    def test_already_paid_order(self, mock_fetch):
        # 첫 번째 검증으로 paid 상태로 변경
        self._post({'imp_uid': 'imp_ok', 'merchant_uid': 'test_merchant_uid'})
        # 두 번째 요청 → 이미 결제 완료
        resp = self._post({'imp_uid': 'imp_ok2', 'merchant_uid': 'test_merchant_uid'})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('이미 결제 완료', resp.data['detail'])

    def test_unauthenticated(self):
        resp = self.client.post(VERIFY_URL, {
            'imp_uid': 'imp_x', 'merchant_uid': 'test_merchant_uid'
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('payments.views.fetch_payment', side_effect=Exception('PortOne 연결 실패'))
    def test_portone_api_error(self, mock_fetch):
        resp = self._post({'imp_uid': 'imp_err', 'merchant_uid': 'test_merchant_uid'})
        self.assertEqual(resp.status_code, status.HTTP_502_BAD_GATEWAY)


class PaymentCancelTest(APITestCase):
    def setUp(self):
        self.buyer = make_user()
        self.token = get_token(self.client, 'buyer@test.com')

    def _post(self, data):
        return self.client.post(CANCEL_URL, data, format='json', **auth(self.token))

    def test_order_not_found(self):
        resp = self._post({'order_id': 99999, 'reason': '변심'})
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_cannot_cancel_pending_order(self):
        order = make_pending_order(self.buyer)
        resp = self._post({'order_id': order.pk, 'reason': '변심'})
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    @patch('payments.views.cancel_payment', return_value={'imp_uid': 'imp_test_uid'})
    def test_cancel_success(self, mock_cancel):
        order = make_paid_order(self.buyer)
        resp = self._post({'order_id': order.pk, 'reason': '단순 변심'})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn('취소 완료', resp.data['detail'])

        order.refresh_from_db()
        self.assertEqual(order.status, Order.Status.CANCELLED)
        order.product.refresh_from_db()
        self.assertEqual(order.product.status, 'on_sale')
        order.payment.refresh_from_db()
        self.assertEqual(order.payment.status, Payment.Status.CANCELLED)

    @patch('payments.views.cancel_payment', side_effect=Exception('취소 API 오류'))
    def test_portone_cancel_error(self, mock_cancel):
        order = make_paid_order(self.buyer)
        resp = self._post({'order_id': order.pk, 'reason': '변심'})
        self.assertEqual(resp.status_code, status.HTTP_502_BAD_GATEWAY)

    def test_unauthenticated(self):
        resp = self.client.post(CANCEL_URL, {'order_id': 1}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('payments.views.cancel_payment', return_value={})
    def test_other_buyer_cannot_cancel(self, mock_cancel):
        other = User.objects.create_user(email='other@test.com', nickname='타인', password='pass1234')
        other_token = get_token(self.client, 'other@test.com')
        order = make_paid_order(self.buyer)
        resp = self.client.post(CANCEL_URL, {'order_id': order.pk, 'reason': '변심'},
                                format='json', **auth(other_token))
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
