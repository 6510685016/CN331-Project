# Generated by Django 5.1.3 on 2024-12-03 13:49

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models
from django.utils.timezone import now


class Migration(migrations.Migration):

    dependencies = [
        ('mainapp', '0011_alter_mission_pic'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='mission',
            name='pic',
        ),
        migrations.AddField(
            model_name='scope',
            name='expense_goal',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=20),
        ),
        migrations.AddField(
            model_name='scope',
            name='income_goal',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=20),
        ),
        migrations.AddField(
            model_name='scope',
            name='month',
            field=models.PositiveIntegerField(default=now().month),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='scope',
            name='year',
            field=models.PositiveIntegerField(default=now().year),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='mission',
            name='amount',
            field=models.DecimalField(decimal_places=2, max_digits=20),
        ),
        migrations.AlterField(
            model_name='mission',
            name='curAmount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=20),
        ),
        migrations.AlterField(
            model_name='scope',
            name='wallet',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='monthly_goals', to='mainapp.wallet'),
        ),
        migrations.AlterField(
            model_name='statement',
            name='amount',
            field=models.DecimalField(decimal_places=2, max_digits=20),
        ),
        migrations.RemoveField(
            model_name='scope',
            name='amount',
        ),
        migrations.RemoveField(
            model_name='scope',
            name='range',
        ),
        migrations.RemoveField(
            model_name='scope',
            name='type',
        ),
        migrations.AlterUniqueTogether(
            name='scope',
            unique_together={('wallet', 'month', 'year')},
        ),
    ]
