from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Product
from .serializers import ProductCreateSerializer, ProductSerializer, ProductStatusSerializer


class ProductListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        qs = Product.objects.select_related('seller')
        category = self.request.query_params.get('category')
        keyword = self.request.query_params.get('q')
        status_param = self.request.query_params.get('status')

        if category:
            qs = qs.filter(category=category)
        if keyword:
            qs = qs.filter(title__icontains=keyword)
        if status_param:
            qs = qs.filter(status=status_param)
        return qs

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ProductCreateSerializer
        return ProductSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        product = serializer.save()
        return Response(ProductSerializer(product).data, status=status.HTTP_201_CREATED)


class ProductDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Product.objects.select_related('seller')
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH'):
            return ProductCreateSerializer
        return ProductSerializer

    def _check_owner(self, product):
        if product.seller != self.request.user:
            raise PermissionDenied('본인의 상품만 수정/삭제할 수 있습니다.')

    def update(self, request, *args, **kwargs):
        product = self.get_object()
        self._check_owner(product)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        product = self.get_object()
        self._check_owner(product)
        return super().destroy(request, *args, **kwargs)


class ProductStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            product = Product.objects.get(pk=pk, seller=request.user)
        except Product.DoesNotExist:
            return Response({'detail': '상품을 찾을 수 없거나 권한이 없습니다.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = ProductStatusSerializer(product, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ProductSerializer(product).data)


class MyProductListView(generics.ListAPIView):
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Product.objects.filter(seller=self.request.user)
