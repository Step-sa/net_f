import yaml
from django.core.management.base import BaseCommand
from django.db import transaction
from backend.models import Shop, Category, Product, ProductInfo, Parameter, ProductParameter


class Command(BaseCommand):
    help = 'Imports products from YAML file'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Path to YAML file')

    def handle(self, *args, **options):
        yaml_file_path = options['file_path']

        try:
            with open(yaml_file_path, 'r', encoding='utf-8') as file:
                data = yaml.safe_load(file)

            if not isinstance(data, dict):
                raise ValueError("YAML файл должен содержать словарь с данными магазина")

            with transaction.atomic():
                # Создаем/обновляем магазин
                shop, _ = Shop.objects.get_or_create(
                    name=data['shop'],
                    defaults={'url': ''}
                )

                # Создаем категории
                category_map = {}
                for category_data in data['categories']:
                    category, _ = Category.objects.get_or_create(
                        id=category_data['id'],
                        defaults={'name': category_data['name']}
                    )
                    category_map[category.id] = category
                    category.shops.add(shop)

                # Обрабатываем товары
                for product_data in data['goods']:
                    category_id = product_data['category']
                    if category_id not in category_map:
                        self.stdout.write(self.style.WARNING(
                            f"Категория с id {category_id} не найдена, пропускаем товар {product_data['name']}"
                        ))
                        continue

                    # Создаем/обновляем продукт
                    product, _ = Product.objects.get_or_create(
                        id=product_data['id'],
                        defaults={
                            'name': product_data['name'],
                            'category': category_map[category_id]
                        }
                    )

                    # Создаем информацию о продукте
                    product_info, _ = ProductInfo.objects.update_or_create(
                        product=product,
                        shop=shop,
                        defaults={
                            'name': product_data['model'],
                            'price': product_data['price'],
                            'price_rrc': product_data['price_rrc'],
                            'quantity': product_data['quantity']
                        }
                    )

                    # Обрабатываем параметры
                    for param_name, param_value in product_data.get('parameters', {}).items():
                        parameter, _ = Parameter.objects.get_or_create(name=param_name)
                        ProductParameter.objects.update_or_create(
                            product_info=product_info,
                            parameter=parameter,
                            defaults={'value': str(param_value)}
                        )

            self.stdout.write(self.style.SUCCESS(
                f"Успешно импортирован магазин {data['shop']} с {len(data['goods'])} товарами"
            ))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ошибка: {str(e)}'))