from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.catalog.models import (
    Brand,
    Category,
    Inventory,
    Product,
    ProductImage,
    ProductVariant,
    Store,
    StoreCategory,
    StoreSettings,
)
from apps.monetization.models import SponsoredProduct
from apps.users.models import Role, User, UserRole


STORES = {
    "Dakar Tech": {
        "category": "Électronique",
        "phone": "+221 77 100 20 30",
        "description": "Téléphones, accessoires et équipements électroniques sélectionnés pour le quotidien.",
        "address": "Avenue Cheikh Anta Diop",
        "city": "Dakar",
        "latitude": Decimal("14.692800"),
        "longitude": Decimal("-17.446700"),
    },
    "Maison Teranga": {
        "category": "Maison & Électroménager",
        "phone": "+221 76 220 30 40",
        "description": "Équipements fiables et articles pratiques pour une maison confortable.",
        "address": "Route de Rufisque",
        "city": "Dakar",
        "latitude": Decimal("14.716700"),
        "longitude": Decimal("-17.316700"),
    },
    "Sunu Mode": {
        "category": "Mode",
        "phone": "+221 78 330 40 50",
        "description": "Mode actuelle, accessoires et créations inspirées du savoir-faire sénégalais.",
        "address": "Marché HLM",
        "city": "Dakar",
        "latitude": Decimal("14.704200"),
        "longitude": Decimal("-17.445100"),
    },
    "Ndar Beauté": {
        "category": "Beauté & Bien-être",
        "phone": "+221 75 440 50 60",
        "description": "Soins, beauté et bien-être avec une sélection adaptée aux besoins locaux.",
        "address": "Avenue Général de Gaulle",
        "city": "Saint-Louis",
        "latitude": Decimal("16.032600"),
        "longitude": Decimal("-16.481800"),
    },
}


PRODUCTS = [
    ("Dakar Tech", "Électronique", "Samsung", "Smartphone Galaxy A55 5G", "Smartphone 5G double SIM, écran AMOLED et batterie longue durée.", "229900", 18, "product-phone-blue.jpg"),
    ("Dakar Tech", "Électronique", "Sunu Tech", "Téléphone double SIM 4G", "Téléphone pratique avec double SIM, appareil photo et grande autonomie.", "49900", 32, "product-phone-dual-sim.jpg"),
    ("Dakar Tech", "Électronique", "Samsung", "Téléviseur Samsung 43 pouces 4K", "Smart TV 4K avec applications de streaming et connectivité Wi-Fi.", "289900", 9, "product-tv-samsung-43.jpg"),
    ("Dakar Tech", "Électronique", "Sunu Tech", "Souris sans fil rechargeable", "Souris ergonomique silencieuse avec connexion USB sans fil.", "8500", 45, "product-wireless-mouse.jpg"),
    ("Dakar Tech", "Électronique", "Samsung", "Chargeur Samsung USB-C 25W", "Charge rapide USB-C 25W compatible avec les appareils Samsung récents.", "15000", 38, "Chargeur-Samsung-25W-1-DISPO-scaled.jpg"),
    ("Dakar Tech", "Électronique", "Vision Plus", "Lunettes anti-lumière bleue", "Monture légère avec verres filtrant la lumière bleue des écrans.", "12500", 27, "product-glasses-blue-light.jpg"),
    ("Maison Teranga", "Maison", "Deska", "Réfrigérateur Deska deux portes", "Réfrigérateur spacieux et économe avec compartiment congélateur.", "329000", 7, "product-fridge-deska.jpg"),
    ("Maison Teranga", "Maison", "Fresh Home", "Fontaine à eau électrique", "Fontaine compacte avec eau chaude et froide pour la maison ou le bureau.", "85000", 14, "product-water-dispenser.jpg"),
    ("Maison Teranga", "Maison", "Sunu Home", "Cuisinière à gaz quatre feux", "Cuisinière robuste avec four et quatre brûleurs à gaz.", "165000", 11, "product-gas-stove.jpg"),
    ("Maison Teranga", "Maison", "Sunu Home", "Set de serviettes six pièces", "Ensemble de serviettes douces et absorbantes pour toute la famille.", "18000", 25, "product-towel-set.jpg"),
    ("Sunu Mode", "Mode", "Sunu Style", "Sac à dos élégant pour femme", "Sac à dos léger avec plusieurs compartiments et finitions soignées.", "24500", 21, "product-backpack-woman.jpg"),
    ("Sunu Mode", "Mode", "Sunu Style", "Chaussures homme en cuir", "Chaussures de ville confortables en cuir noir.", "45000", 16, "product-shoes-black-leather.jpg"),
    ("Sunu Mode", "Mode", "Sunu Style", "Montre homme acier inoxydable", "Montre classique avec bracelet en acier et cadran résistant.", "37500", 19, "product-watch-steel-men.jpg"),
    ("Sunu Mode", "Mode", "Teranga Création", "Robe wax élégante", "Robe colorée en tissu wax, confectionnée pour les sorties et cérémonies.", "32000", 13, "Robe.jpg"),
    ("Ndar Beauté", "Beauté", "Ndar Care", "Coffret de soins beauté complet", "Routine complète pour nettoyer, hydrater et protéger la peau.", "27500", 24, "gamme.jpg"),
    ("Ndar Beauté", "Beauté", "Ndar Care", "Kit beauté naturel", "Sélection de soins naturels pour le visage et le corps.", "19500", 30, "category-beaute.jpg"),
]


class Command(BaseCommand):
    help = "Crée un catalogue de démonstration idempotent pour la vitrine SUNU MALL."

    def add_arguments(self, parser):
        parser.add_argument(
            "--if-empty",
            action="store_true",
            help="Ne crée rien lorsqu'un produit public existe déjà.",
        )
        parser.add_argument(
            "--asset-base-url",
            default=settings.FRONTEND_URL,
            help="URL publique contenant les images du catalogue.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["if_empty"] and Product.objects.filter(
            status=Product.Status.ACTIVE,
            store__status=Store.Status.ACTIVE,
        ).exists():
            self.stdout.write(self.style.WARNING("Catalogue public déjà rempli : aucune donnée ajoutée."))
            return

        asset_base_url = options["asset_base_url"].rstrip("/")
        owner = self._owner()
        stores = self._stores(owner)
        categories = self._categories()
        brands = self._brands()
        products = self._products(stores, categories, brands, asset_base_url)
        self._sponsor(products[:4])

        self.stdout.write(
            self.style.SUCCESS(
                f"Catalogue prêt : {len(stores)} boutiques et {len(products)} produits actifs."
            )
        )

    def _owner(self):
        owner, created = User.objects.get_or_create(
            email="catalogue@sunu-mall.sn",
            defaults={
                "username": "catalogue_demo",
                "first_name": "Équipe",
                "last_name": "SUNU MALL",
                "phone": "+221 77 000 00 00",
                "is_verified": True,
                "is_active": True,
            },
        )
        if created:
            owner.set_unusable_password()
            owner.save(update_fields=["password"])

        merchant_role = Role.objects.get(name=Role.RoleName.MERCHANT)
        UserRole.objects.get_or_create(user=owner, role=merchant_role)
        return owner

    def _stores(self, owner):
        stores = {}
        for name, data in STORES.items():
            store_category, _ = StoreCategory.objects.get_or_create(name=data["category"])
            store, _ = Store.objects.update_or_create(
                owner=owner,
                name=name,
                defaults={
                    "category": store_category,
                    "phone": data["phone"],
                    "description": data["description"],
                    "address": data["address"],
                    "city": data["city"],
                    "latitude": data["latitude"],
                    "longitude": data["longitude"],
                    "status": Store.Status.ACTIVE,
                    "rejection_reason": "",
                },
            )
            StoreSettings.objects.get_or_create(
                store=store,
                defaults={
                    "min_order_amount": Decimal("0"),
                    "business_hours": {
                        day: {"open": "09:00", "close": "19:00"}
                        for day in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
                    },
                },
            )
            stores[name] = store
        return stores

    def _categories(self):
        categories = {}
        for name in {product[1] for product in PRODUCTS}:
            category = Category.objects.filter(name=name, parent__isnull=True).first()
            categories[name] = category or Category.objects.create(name=name)
        return categories

    def _brands(self):
        brands = {}
        for name in {product[2] for product in PRODUCTS}:
            brand = Brand.objects.filter(name=name).first()
            brands[name] = brand or Brand.objects.create(name=name)
        return brands

    def _products(self, stores, categories, brands, asset_base_url):
        products = []
        for index, (store_name, category_name, brand_name, name, description, price, stock, image) in enumerate(PRODUCTS, start=1):
            product, _ = Product.objects.update_or_create(
                store=stores[store_name],
                name=name,
                defaults={
                    "category": categories[category_name],
                    "brand": brands[brand_name],
                    "description": description,
                    "base_price": Decimal(price),
                    "status": Product.Status.ACTIVE,
                },
            )
            variant, _ = ProductVariant.objects.update_or_create(
                sku=f"DEMO-SM-{index:03d}",
                defaults={
                    "product": product,
                    "attributes": {"condition": "Neuf"},
                    "price": Decimal(price),
                },
            )
            inventory, inventory_created = Inventory.objects.get_or_create(
                variant=variant,
                defaults={"quantity": stock, "reserved_quantity": 0},
            )
            if not inventory_created and inventory.quantity < inventory.reserved_quantity:
                inventory.quantity = inventory.reserved_quantity
                inventory.save(update_fields=["quantity", "updated_at"])

            ProductImage.objects.update_or_create(
                product=product,
                position=0,
                defaults={"image": None, "minio_path": f"{asset_base_url}/{image}"},
            )
            products.append(product)
        return products

    def _sponsor(self, products):
        today = timezone.now().date()
        for product in products:
            sponsorship = SponsoredProduct.objects.filter(product=product, store=product.store).first()
            values = {
                "daily_budget": Decimal("5000"),
                "starts_at": today,
                "ends_at": today + timedelta(days=365),
                "status": SponsoredProduct.Status.ACTIVE,
            }
            if sponsorship:
                for field, value in values.items():
                    setattr(sponsorship, field, value)
                sponsorship.save(update_fields=[*values, "updated_at"])
            else:
                SponsoredProduct.objects.create(product=product, store=product.store, **values)
