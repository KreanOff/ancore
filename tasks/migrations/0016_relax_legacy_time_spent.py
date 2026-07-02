from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0015_task_parent'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_name = 'tasks_task'
                          AND column_name = 'time_spent'
                    ) THEN
                        ALTER TABLE tasks_task
                        ALTER COLUMN time_spent DROP NOT NULL;
                    END IF;
                END $$;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
