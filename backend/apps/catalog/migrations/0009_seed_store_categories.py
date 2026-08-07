from django.db import migrations

CATEGORIES = [
    "Électronique",
    "Mode",
    "Alimentation",
    "Beauté & Bien-être",
    "Maison & Électroménager",
    "Sport",
]


def seed_categories(apps, schema_editor):
    StoreCategory = apps.get_model("catalog", "StoreCategory")
    for name in CATEGORIES:
        StoreCategory.objects.get_or_create(name=name)


def remove_categories(apps, schema_editor):
    StoreCategory = apps.get_model("catalog", "StoreCategory")
    StoreCategory.objects.filter(name__in=CATEGORIES).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0008_store_address_store_city_store_description_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_categories, remove_categories),
    ]
