from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings

class Migration(migrations.Migration):

    dependencies = [
        ('transfer_app', '0004_batch_transferrequest_batch'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='batch',
            name='designated_lead',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='batches_designated', to=settings.AUTH_USER_MODEL, verbose_name='Lead duyệt'),
        ),
    ]
