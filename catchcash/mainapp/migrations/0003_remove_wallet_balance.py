# Generated by Django 5.1.3 on 2024-11-12 15:00

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mainapp', '0002_remove_mission_account_remove_preset_account_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='wallet',
            name='balance',
        ),
    ]
