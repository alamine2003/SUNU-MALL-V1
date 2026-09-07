from django.db import migrations


def seed_roles(apps, schema_editor):
    Role = apps.get_model("users", "Role")
    descriptions = {
        "admin": "Administrateur de la plateforme",
        "merchant": "Commerçant",
        "client": "Client",
        "driver": "Livreur",
    }
    for name, description in descriptions.items():
        Role.objects.get_or_create(name=name, defaults={"description": description})


class Migration(migrations.Migration):
    dependencies = [("users", "0002_alter_role_name")]

    operations = [migrations.RunPython(seed_roles, migrations.RunPython.noop)]
