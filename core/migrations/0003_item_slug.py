# Generated by Django 4.0.1 on 2022-01-19 07:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_item_category_item_label'),
    ]

    operations = [
        migrations.AddField(
            model_name='item',
            name='slug',
            field=models.SlugField(default=''),
            preserve_default=False,
        ),
    ]
