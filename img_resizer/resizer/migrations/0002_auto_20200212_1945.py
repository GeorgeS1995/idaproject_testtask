# Generated by Django 3.0.3 on 2020-02-12 16:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('resizer', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='image',
            options={'ordering': ['id']},
        ),
        migrations.AlterField(
            model_name='image',
            name='photo',
            field=models.ImageField(blank=True, upload_to=''),
        ),
    ]
