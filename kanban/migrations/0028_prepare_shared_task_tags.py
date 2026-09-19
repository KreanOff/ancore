from django.db import migrations


class Migration(migrations.Migration):
    """Restore the missing historical migration node.

    The project models have since moved tag ownership to ``tasks``.  The
    current schema reconciliation migration is generated after this restored
    chain, so this node intentionally carries no database operation.
    """

    dependencies = [
        ('kanban', '0027_remove_kanbantag_unique_kanban_tag_per_user_and_more'),
    ]

    operations = []
