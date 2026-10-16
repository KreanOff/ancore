from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('kanban', '0013_task_time_spent'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE kanban_kanban
                ADD COLUMN IF NOT EXISTS time_spent_hours integer NULL;

                ALTER TABLE kanban_kanban
                ADD COLUMN IF NOT EXISTS time_spent_minutes integer NULL;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
