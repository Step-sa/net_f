from django.core.mail import send_mail
from django.conf import settings
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string
from .models import (
    Shop, Product, ProductInfo, Parameter, ProductParameter,
    Cart, CartItem, Contact, Order, OrderItem
)

User = get_user_model()

# --- Auth ---
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'email', 'password')

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data['email'],
            email=validated_data['email'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            password=validated_data['password']
        )

class AuthSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

# --- Products ---
class ParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parameter
        fields = ('name',)

class ProductParameterSerializer(serializers.ModelSerializer):
    parameter = ParameterSerializer()

    class Meta:
        model = ProductParameter
        fields = ('parameter', 'value')

class ShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ('name',)

class ProductSerializer(serializers.ModelSerializer):
    category = serializers.StringRelatedField()

    class Meta:
        model = Product
        fields = ('name', 'category')

class ProductInfoSerializer(serializers.ModelSerializer):
    product = ProductSerializer()
    shop = ShopSerializer()
    product_parameters = ProductParameterSerializer(many=True)

    class Meta:
        model = ProductInfo
        fields = ('id', 'product', 'shop', 'price', 'quantity', 'product_parameters')

# --- Cart ---
class CartItemSerializer(serializers.ModelSerializer):
    product_info = ProductInfoSerializer(read_only=True)
    product_info_id = serializers.PrimaryKeyRelatedField(
        queryset=ProductInfo.objects.all(), source='product_info', write_only=True
    )

    class Meta:
        model = CartItem
        fields = ('id', 'product_info', 'product_info_id', 'quantity', 'price')

class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ('id', 'items', 'total')

    def get_total(self, obj):
        return sum([it.quantity * it.price for it in obj.items.all()])

# --- Contact ---
class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = '__all__'
        read_only_fields = ('user',)

# --- Orders ---
class OrderItemSerializer(serializers.ModelSerializer):
    product_info = ProductInfoSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = ('id', 'product_info', 'quantity', 'price')

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    contact = ContactSerializer(read_only=True)
    status_history = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ('id', 'number', 'created_at', 'total', 'status', 'contact', 'items', 'status_history')

    def get_status_history(self, obj):
        return [
            {'status': s.status, 'changed_at': s.changed_at, 'note': s.note}
            for s in obj.status_history.all()
        ]

class CreateOrderSerializer(serializers.Serializer):
    cart_id = serializers.IntegerField()
    contact_id = serializers.IntegerField()

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    email_confirm_token = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'email', 'password', 'email_confirm_token')

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['email'],
            email=validated_data['email'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            password=validated_data['password'],
            is_active=False  # пользователь неактивен пока не подтвердит почту
        )
        token = get_random_string(20)
        user.email_confirm_token = token
        user.save()

        # Отправка письма с подтверждением
        confirm_link = f"http://localhost:8000/api/auth/confirm-email/?token={token}"
        send_mail(
            'Подтверждение регистрации',
            f'Перейдите по ссылке для подтверждения: {confirm_link}',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        return user