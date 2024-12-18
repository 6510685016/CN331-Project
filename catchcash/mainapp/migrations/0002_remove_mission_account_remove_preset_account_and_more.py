# Generated by Django 5.1.3 on 2024-11-11 09:31

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mainapp', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='mission',
            name='account',
        ),
        migrations.RemoveField(
            model_name='preset',
            name='account',
        ),
        migrations.AddField(
            model_name='mission',
            name='wallet',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='missions', to='mainapp.wallet'),
        ),
        migrations.AddField(
            model_name='preset',
            name='wallet',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='presets', to='mainapp.wallet'),
        ),
        migrations.AlterField(
            model_name='account',
            name='lastLoginDate',
            field=models.DateField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='fixstatement',
            name='wallet',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='fix_statements', to='mainapp.wallet'),
        ),
        migrations.AlterField(
            model_name='scope',
            name='wallet',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='scopes', to='mainapp.wallet'),
        ),
        migrations.AlterField(
            model_name='statement',
            name='wallet',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='statements', to='mainapp.wallet'),
        ),
        migrations.AlterField(
            model_name='wallet',
            name='listCategory',
            field=models.JSONField(default=list),
        ),
    ]
