from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('tasks', '0050_task_work_log'),
    ]

    operations = [
        # Some databases retain this NOT NULL column from a retired timer.
        # Task no longer writes it. Keep historical values and let new rows
        # use zero, without adding the legacy column to fresh databases.
        migrations.RunSQL(
            sql="""
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_schema = current_schema()
                          AND table_name = 'tasks_task'
                          AND column_name = 'logged_seconds'
                          AND column_default IS NULL
                    ) THEN
                        ALTER TABLE tasks_task
                        ALTER COLUMN logged_seconds SET DEFAULT 0;
                    END IF;
                END $$;
            """,
            # Rolling back must not reintroduce failed Task inserts.
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
