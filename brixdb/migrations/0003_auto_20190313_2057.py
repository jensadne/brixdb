# Generated by Django 2.1.7 on 2019-03-13 19:57

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('brixdb', '0002_auto_20190313_2047'),
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=256)),
                ('bl_id', models.CharField(max_length=16)),
            ],
        ),
        migrations.RemoveField(
            model_name='bricklinkcategory',
            name='parent',
        ),
        migrations.AlterField(
            model_name='catalogitem',
            name='category',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='brixdb.Category'),
        ),
        migrations.AddField(
            model_name='category',
            name='bl_category',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='brixdb.BricklinkCategory'),
        ),
        migrations.AddField(
            model_name='category',
            name='parent',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='sub_categories', to='brixdb.Category'),
        ),
    ]