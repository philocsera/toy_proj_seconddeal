from django.utils import timezone
from django.views.generic import TemplateView
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.models import Order
from .models import Payment
from .portone import cancel_payment, fetch_payment


class CheckoutPageView(TemplateView):
    template_name = 'payments/checkout.html'


class PaymentVerifyView(APIView):
    """
    결제 완료 후 클라이언트가 imp_uid와 merchant_uid를 전송.
    PortOne 서버에 직접 조회해 금액을 재검증한다 (위변조 방지).

    POST /api/payments/verify/
    Body: { "imp_uid": "...", "merchant_uid": "..." }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        imp_uid = request.data.get('imp_uid')
        merchant_uid = request.data.get('merchant_uid')

        if not imp_uid or not merchant_uid:
            return Response({'detail': 'imp_uid, merchant_uid가 필요합니다.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            order = Order.objects.get(merchant_uid=merchant_uid, buyer=request.user)
        except Order.DoesNotExist:
            return Response({'detail': '주문을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

        if order.status == Order.Status.PAID:
            return Response({'detail': '이미 결제 완료된 주문입니다.'}, status=status.HTTP_400_BAD_REQUEST)

        # PortOne 서버에서 실제 결제 정보 조회
        try:
            paid_info = fetch_payment(imp_uid)
        except Exception as e:
            return Response({'detail': f'PortOne API 오류: {e}'}, status=status.HTTP_502_BAD_GATEWAY)

        # 금액 검증: 서버가 알고 있는 주문 금액 vs PortOne에서 실제 승인된 금액
        if paid_info['amount'] != order.total_price:
            return Response(
                {'detail': f'결제 금액 불일치 (주문: {order.total_price}, 실제: {paid_info["amount"]})'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if paid_info['status'] != 'paid':
            return Response({'detail': f'결제 상태 이상: {paid_info["status"]}'}, status=status.HTTP_400_BAD_REQUEST)

        # 검증 통과 → 주문·결제 상태 업데이트
        order.status = Order.Status.PAID
        order.save(update_fields=['status'])

        order.product.status = 'sold'
        order.product.save(update_fields=['status'])

        Payment.objects.create(
            order=order,
            imp_uid=imp_uid,
            merchant_uid=merchant_uid,
            amount=paid_info['amount'],
            status=Payment.Status.PAID,
            paid_at=timezone.now(),
        )

        return Response({'detail': '결제 검증 완료', 'order_id': order.id})


class PaymentCancelView(APIView):
    """
    결제 취소. 본인 주문만 취소 가능.

    POST /api/payments/cancel/
    Body: { "order_id": 1, "reason": "단순 변심" }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        order_id = request.data.get('order_id')
        reason = request.data.get('reason', '구매자 요청')

        try:
            order = Order.objects.get(pk=order_id, buyer=request.user, status=Order.Status.PAID)
            payment = order.payment
        except Order.DoesNotExist:
            return Response({'detail': '결제 완료 주문을 찾을 수 없습니다.'}, status=status.HTTP_404_NOT_FOUND)
        except Payment.DoesNotExist:
            return Response({'detail': '결제 정보가 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            cancel_payment(payment.imp_uid, reason)
        except Exception as e:
            return Response({'detail': f'취소 실패: {e}'}, status=status.HTTP_502_BAD_GATEWAY)

        order.status = Order.Status.CANCELLED
        order.save(update_fields=['status'])

        order.product.status = 'on_sale'
        order.product.save(update_fields=['status'])

        payment.status = Payment.Status.CANCELLED
        payment.save(update_fields=['status'])

        return Response({'detail': '결제 취소 완료'})
