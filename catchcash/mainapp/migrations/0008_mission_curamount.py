# Generated by Django 5.1.3 on 2024-11-21 19:01

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mainapp', '0007_rename_inittarget_scope_amount_remove_scope_spendmax_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='mission',
            name='curAmount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
            preserve_default=False,
        ),
    ]
