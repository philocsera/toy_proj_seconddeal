from django.urls import path

from .views import MyOrderListView, OrderCreateView

urlpatterns = [
    path('', OrderCreateView.as_view(), name='order-create'),
    path('mine/', MyOrderListView.as_view(), name='my-orders'),
]
