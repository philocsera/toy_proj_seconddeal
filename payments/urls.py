from django.urls import path

from .views import CheckoutPageView, PaymentCancelView, PaymentVerifyView

urlpatterns = [
    path('checkout/', CheckoutPageView.as_view(), name='checkout'),
    path('verify/', PaymentVerifyView.as_view(), name='payment-verify'),
    path('cancel/', PaymentCancelView.as_view(), name='payment-cancel'),
]
