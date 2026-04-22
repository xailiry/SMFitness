"""
Data migration: seeds the Exercise table from fixtures/exercises.json.

Render free tier wipes the SQLite file whenever the service spins down,
so we reload the base exercise catalog on every deploy via migrate.

Runs idempotently — existing rows with matching PK are updated in place
via update_or_create, so no duplicates are produced on repeated runs.
"""
from pathlib import Path
import json

from django.db import migrations


FIXTURE = Path(__file__).resolve().parent.parent / "fixtures" / "exercises.json"


def seed_exercises(apps, schema_editor):
    Exercise = apps.get_model("fitness", "Exercise")

    if not FIXTURE.exists():
        # Fixture missing — skip silently so migrate doesn't fail in dev.
        return

    with FIXTURE.open(encoding="utf-8") as f:
        records = json.load(f)

    for rec in records:
        pk = rec["pk"]
        fields = rec["fields"]
        Exercise.objects.update_or_create(
            pk=pk,
            defaults={
                "name": fields.get("name", ""),
                "description": fields.get("description"),
                "muscle_group": fields.get("muscle_group") or "other",
            },
        )


def unseed_exercises(apps, schema_editor):
    # No-op: we don't want migrate --reverse to delete a user's catalog.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("fitness", "0017_workout_body_weight_alter_weightlog_date"),
    ]

    operations = [
        migrations.RunPython(seed_exercises, unseed_exercises),
    ]
