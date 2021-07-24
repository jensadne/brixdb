# Generated by Django 3.2.5 on 2021-07-23 13:13

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('brixdb', '0011_colour_other_names'),
    ]

    operations = [
        migrations.CreateModel(
            name='BnPElement',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tlg_element_id', models.PositiveIntegerField()),
                ('image_url', models.URLField(default='', max_length=512)),
                ('last_updated', models.DateTimeField(default=django.utils.timezone.now)),
                ('sold_out', models.BooleanField(default=False)),
                ('available', models.BooleanField(default=True)),
            ],
        ),
        migrations.AlterField(
            model_name='bricklinkcategory',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
        migrations.AlterField(
            model_name='catalogitem',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
        migrations.AlterField(
            model_name='catalogitem',
            name='other_names',
            field=models.JSONField(default=list),
        ),
        migrations.AlterField(
            model_name='catalogitem',
            name='other_numbers',
            field=models.JSONField(default=list),
        ),
        migrations.AlterField(
            model_name='category',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
        migrations.AlterField(
            model_name='colour',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
        migrations.AlterField(
            model_name='colour',
            name='other_names',
            field=models.JSONField(default=list),
        ),
        migrations.AlterField(
            model_name='element',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
        migrations.AlterField(
            model_name='element',
            name='lego_ids',
            field=models.JSONField(default=list),
        ),
        migrations.AlterField(
            model_name='iteminventory',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
        migrations.AlterField(
            model_name='owneditem',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
        migrations.AlterField(
            model_name='user',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
        migrations.CreateModel(
            name='BnPElementPrices',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_seen', models.DateTimeField(default=django.utils.timezone.now)),
                ('currency', models.CharField(max_length=3)),
                ('price', models.DecimalField(decimal_places=2, max_digits=9)),
                ('element', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='prices', to='brixdb.bnpelement')),
            ],
        ),
        migrations.AddField(
            model_name='bnpelement',
            name='element',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='brixdb.element'),
        ),
    ]
