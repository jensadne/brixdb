# Generated by Django 2.1.7 on 2019-05-01 12:32

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('brixdb', '0007_auto_20190329_2139'),
    ]

    operations = [
        migrations.RenameField(
            model_name='itemowned',
            old_name='owned_item',
            new_name='item',
        ),
        migrations.AlterField(
            model_name='catalogitem',
            name='item_type',
            field=models.CharField(choices=[('set', 'Set'), ('part', 'Part'), ('minifig', 'Minifig'), ('gear', 'Gear'), ('book', 'Book')], default='part', max_length=16),
        ),
        migrations.AlterField(
            model_name='itemowned',
            name='owner',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='owned_items', to=settings.AUTH_USER_MODEL),
        ),
    ]
