import uuid

from django.db import migrations, models


def generar_tokens(apps, schema_editor):
    """Da un token propio a cada carrito que ya existiera."""
    Carrito = apps.get_model("catalogo", "Carrito")
    for carrito in Carrito.objects.all():
        carrito.token = uuid.uuid4()
        carrito.save(update_fields=["token"])


class Migration(migrations.Migration):

    dependencies = [
        ("catalogo", "0001_initial"),
    ]

    operations = [
        # 1) Se agrega sin unicidad para poder rellenar los carritos existentes.
        migrations.AddField(
            model_name="carrito",
            name="token",
            field=models.UUIDField(editable=False, null=True),
        ),
        # 2) Cada carrito existente recibe un token distinto.
        migrations.RunPython(generar_tokens, migrations.RunPython.noop),
        # 3) Ya con valores únicos, se exige unicidad.
        migrations.AlterField(
            model_name="carrito",
            name="token",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
