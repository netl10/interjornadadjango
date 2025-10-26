# Generated manually for adding is_manual field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('logs', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='accesslog',
            name='is_manual',
            field=models.BooleanField(default=False, verbose_name='Log Manual'),
        ),
    ]
