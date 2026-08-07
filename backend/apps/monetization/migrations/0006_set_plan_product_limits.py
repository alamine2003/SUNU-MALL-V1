from django.db import migrations


PLAN_LIMITS = {
    "Standard": 10,
    "Premium": 50,
    "Premium+": None,
}


def set_limits(apps, schema_editor):
    SubscriptionPlan = apps.get_model("monetization", "SubscriptionPlan")
    for name, limit in PLAN_LIMITS.items():
        SubscriptionPlan.objects.filter(name=name).update(max_products=limit)


def unset_limits(apps, schema_editor):
    SubscriptionPlan = apps.get_model("monetization", "SubscriptionPlan")
    SubscriptionPlan.objects.filter(name__in=PLAN_LIMITS.keys()).update(max_products=None)


class Migration(migrations.Migration):

    dependencies = [
        ("monetization", "0005_subscriptionplan_max_products"),
    ]

    operations = [
        migrations.RunPython(set_limits, unset_limits),
    ]
