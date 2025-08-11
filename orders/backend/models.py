from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _


class Shop(models.Model):
    name = models.CharField(max_length=100, verbose_name='Название')
    url = models.URLField(verbose_name='Ссылка', null=True, blank=True)

    class Meta:
        verbose_name = 'Магазин'
        verbose_name_plural = 'Магазины'
        ordering = ('-name',)

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=50, verbose_name='Название')
    shops = models.ManyToManyField(Shop, verbose_name='Магазины', related_name='categories', blank=True)

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=100, verbose_name='Название')
    category = models.ForeignKey(Category, verbose_name='Категория', related_name='products',
                                 on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Продукт'
        verbose_name_plural = 'Продукты'
        constraints = [
            models.UniqueConstraint(fields=['name', 'category'], name='unique_product_category')
        ]

    def __str__(self):
        return f'{self.name} ({self.category.name})'


class Parameter(models.Model):
    name = models.CharField(max_length=50, verbose_name='Название')

    class Meta:
        verbose_name = 'Параметр'
        verbose_name_plural = 'Параметры'

    def __str__(self):
        return self.name


class ProductInfo(models.Model):
    product = models.ForeignKey(Product, verbose_name='Продукт', related_name='product_infos',
                                on_delete=models.CASCADE)
    shop = models.ForeignKey(Shop, verbose_name='Магазин', related_name='product_infos',
                             on_delete=models.CASCADE)
    name = models.CharField(max_length=100, verbose_name='Название')
    quantity = models.PositiveIntegerField(verbose_name='Количество')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена',
                                validators=[MinValueValidator(0)])
    price_rrc = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Рекомендуемая цена',
                                    validators=[MinValueValidator(0)])
    parameters = models.ManyToManyField(Parameter, through='ProductParameter',
                                        verbose_name='Параметры', related_name='product_infos')

    class Meta:
        verbose_name = 'Информация о продукте'
        verbose_name_plural = 'Информация о продуктах'
        constraints = [
            models.UniqueConstraint(fields=['product', 'shop'], name='unique_product_info')
        ]

    def __str__(self):
        return f'{self.product.name} ({self.shop.name})'


class ProductParameter(models.Model):
    product_info = models.ForeignKey(ProductInfo, verbose_name='Информация о продукте',
                                     related_name='product_parameters', on_delete=models.CASCADE)
    parameter = models.ForeignKey(Parameter, verbose_name='Параметр',
                                  related_name='product_parameters', on_delete=models.CASCADE)
    value = models.CharField(max_length=100, verbose_name='Значение')

    class Meta:
        verbose_name = 'Параметр продукта'
        verbose_name_plural = 'Параметры продуктов'
        constraints = [
            models.UniqueConstraint(fields=['product_info', 'parameter'], name='unique_product_parameter')
        ]

    def __str__(self):
        return f'{self.parameter.name} - {self.value}'


class Order(models.Model):
    class StatusChoices(models.TextChoices):
        BASKET = 'basket', _('Корзина')
        NEW = 'new', _('Новый')
        CONFIRMED = 'confirmed', _('Подтвержден')
        ASSEMBLED = 'assembled', _('Собран')
        SENT = 'sent', _('Отправлен')
        DELIVERED = 'delivered', _('Доставлен')
        CANCELED = 'canceled', _('Отменен')

    user = models.ForeignKey(User, verbose_name='Пользователь', related_name='orders',
                             on_delete=models.CASCADE)
    dt = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    status = models.CharField(max_length=15, choices=StatusChoices.choices,
                              default=StatusChoices.BASKET, verbose_name='Статус')

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ('-dt',)

    def __str__(self) -> str:
        return f'Заказ {self.pk} от {self.dt}' if self.pk else 'Новый заказ'


class OrderItem(models.Model):
    order = models.ForeignKey(Order, verbose_name='Заказ', related_name='ordered_items',
                              on_delete=models.CASCADE)
    product = models.ForeignKey(Product, verbose_name='Продукт', related_name='ordered_items',
                                on_delete=models.CASCADE)
    shop = models.ForeignKey(Shop, verbose_name='Магазин', related_name='ordered_items',
                             on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(verbose_name='Количество',
                                           validators=[MinValueValidator(1)])

    class Meta:
        verbose_name = 'Элемент заказа'
        verbose_name_plural = 'Элементы заказа'
        constraints = [
            models.UniqueConstraint(fields=['order', 'product', 'shop'], name='unique_order_item')
        ]

    def __str__(self):
        return f'{self.product.name} x{self.quantity} ({self.shop.name})'


class Contact(models.Model):
    class TypeChoices(models.TextChoices):
        PHONE = 'phone', _('Телефон')
        EMAIL = 'email', _('Email')
        ADDRESS = 'address', _('Адрес')

    type = models.CharField(max_length=10, choices=TypeChoices.choices, verbose_name='Тип')
    user = models.ForeignKey(User, verbose_name='Пользователь', related_name='contacts',
                             on_delete=models.CASCADE)
    value = models.CharField(max_length=200, verbose_name='Значение')

    class Meta:
        verbose_name = 'Контакт'
        verbose_name_plural = 'Контакты'

    def __str__(self) -> str:
        return f'{self.TypeChoices(self.type).label}: {self.value}'