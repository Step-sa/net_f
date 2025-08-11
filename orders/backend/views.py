from django.contrib.auth import authenticate, get_user_model
from rest_framework import generics, status, viewsets, mixins, permissions
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authtoken.models import Token
from django.shortcuts import get_object_or_404
from django.db import transaction
from .models import (
    ProductInfo, Cart, CartItem, Contact, Order, OrderItem, OrderStatusHistory, User
)
from .serializers import (
    RegisterSerializer, AuthSerializer,
    ProductInfoSerializer, CartSerializer, CartItemSerializer,
    ContactSerializer, OrderSerializer, CreateOrderSerializer
)

User = get_user_model()

# --- Auth ---
class RegisterView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = RegisterSerializer

@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    ser = AuthSerializer(data=request.data)
    ser.is_valid(raise_exception=True)
    user = authenticate(
        username=ser.validated_data['email'],
        password=ser.validated_data['password']
    )
    if not user:
        return Response({'detail': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
    token, _ = Token.objects.get_or_create(user=user)
    return Response({'token': token.key})

# --- Products ---
class ProductInfoListView(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProductInfoSerializer
    queryset = ProductInfo.objects.select_related('product', 'shop').prefetch_related('product_parameters')

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(product__name__icontains=search)
        return qs

class ProductInfoDetailView(generics.RetrieveAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProductInfoSerializer
    queryset = ProductInfo.objects.select_related('product', 'shop').prefetch_related('product_parameters')

# --- Cart ---
class CartView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CartSerializer

    def get_object(self):
        cart, _ = Cart.objects.get_or_create(user=self.request.user)
        return cart

class AddCartItemView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CartItemSerializer

    def perform_create(self, serializer):
        cart, _ = Cart.objects.get_or_create(user=self.request.user)
        product_info = serializer.validated_data['product_info']
        qty = serializer.validated_data['quantity']
        item, created = CartItem.objects.get_or_create(
            cart=cart, product_info=product_info,
            defaults={'quantity': qty, 'price': product_info.price}
        )
        if not created:
            item.quantity += qty
            item.save()

class RemoveCartItemView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]
    queryset = CartItem.objects.all()

    def get_object(self):
        return get_object_or_404(
            CartItem, pk=self.kwargs['pk'], cart__user=self.request.user
        )

# --- Contacts ---
class ContactViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = ContactSerializer

    def get_queryset(self):
        return Contact.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

# --- Orders ---
class OrderViewSet(viewsets.GenericViewSet, mixins.ListModelMixin, mixins.RetrieveModelMixin):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer

    def get_queryset(self):
        if self.request.user.is_staff:
            return Order.objects.all()
        return Order.objects.filter(user=self.request.user)

    @action(detail=False, methods=['post'])
    def create_from_cart(self, request):
        ser = CreateOrderSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        cart = get_object_or_404(Cart, pk=ser.validated_data['cart_id'], user=request.user)
        contact = get_object_or_404(Contact, pk=ser.validated_data['contact_id'], user=request.user)

        if not cart.items.exists():
            return Response({'detail': 'Cart is empty'}, status=400)

        with transaction.atomic():
            order = Order.objects.create(
                user=request.user,
                contact=contact,
                total=sum(i.quantity * i.price for i in cart.items.all()),
                status='new'
            )
            for item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    product_info=item.product_info,
                    quantity=item.quantity,
                    price=item.price
                )
            OrderStatusHistory.objects.create(order=order, status='new')
            cart.items.all().delete()

        return Response(OrderSerializer(order).data, status=201)

    @action(detail=True, methods=['post'])
    def change_status(self, request, pk=None):
        if not request.user.is_staff:
            return Response({'detail': 'Permission denied'}, status=403)
        order = self.get_object()
        new_status = request.data.get('status')
        note = request.data.get('note', '')
        order.status = new_status
        order.save()
        OrderStatusHistory.objects.create(order=order, status=new_status, note=note)
        return Response(OrderSerializer(order).data)



@api_view(['GET'])
def confirm_email(request):
    token = request.query_params.get('token')
    try:
        user = User.objects.get(email_confirm_token=token)
        user.is_active = True
        user.email_confirm_token = ''
        user.save()
        return Response({'detail': 'Email подтвержден, можете войти.'})
    except User.DoesNotExist:
        return Response({'detail': 'Неверный токен подтверждения'}, status=400)


class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Возвращаем только заказы текущего пользователя
        return Order.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        # Пример дополнительного действия — подтверждение заказа
        order = self.get_object()
        order.status = 'confirmed'  # или нужный статус
        order.save()
        return Response({'status': 'order confirmed'})

class CustomAuthToken(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                           context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'email': user.email
        })