from django.urls import path, include
from rest_framework.routers import DefaultRouter
from backend.views import CustomAuthToken
from backend.views import (
    RegisterView, login_view,
    ProductInfoListView, ProductInfoDetailView,
    CartView, AddCartItemView, RemoveCartItemView,
    ContactViewSet, OrderViewSet
)

router = DefaultRouter()
router.register(r'contacts', ContactViewSet, basename='contacts')
router.register(r'orders', OrderViewSet, basename='orders')

urlpatterns = [
    path('auth/register/', RegisterView.as_view()),
    path('auth/login/', login_view),
    path('products/', ProductInfoListView.as_view()),
    path('products/<int:pk>/', ProductInfoDetailView.as_view()),
    path('cart/', CartView.as_view()),
    path('cart/add/', AddCartItemView.as_view()),
    path('cart/item/<int:pk>/remove/', RemoveCartItemView.as_view()),
    path('', include(router.urls)),
    path('auth/login/', CustomAuthToken.as_view(), name='api_token_auth'),
]
