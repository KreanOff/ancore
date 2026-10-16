from collections import defaultdict

from django.db import migrations
from django.utils.text import slugify


POLISH_CODE_TRANSLATION = str.maketrans({
    'ą': 'a', 'ć': 'c', 'ę': 'e', 'ł': 'l', 'ń': 'n', 'ó': 'o', 'ś': 's', 'ź': 'z', 'ż': 'z',
    'Ą': 'A', 'Ć': 'C', 'Ę': 'E', 'Ł': 'L', 'Ń': 'N', 'Ó': 'O', 'Ś': 'S', 'Ź': 'Z', 'Ż': 'Z',
})


def backfill_workplace_codes(apps, schema_editor):
    Workplace = apps.get_model('workplaces', 'Workplace')
    used_codes = defaultdict(set)

    for owner_id, code in Workplace.objects.exclude(code='').values_list('owner_id', 'code').iterator():
        used_codes[owner_id].add(code.strip().upper())

    workplaces = Workplace.objects.filter(code='').order_by('owner_id', 'id')
    for workplace in workplaces.iterator():
        normalized_name = (workplace.name or '').translate(POLISH_CODE_TRANSLATION)
        base_code = (slugify(normalized_name)[:20] or 'miejsce').upper()
        candidate = base_code
        counter = 2
        while candidate in used_codes[workplace.owner_id]:
            suffix = f'-{counter}'
            candidate = f'{base_code[:20 - len(suffix)]}{suffix}'
            counter += 1

        Workplace.objects.filter(pk=workplace.pk).update(code=candidate)
        used_codes[workplace.owner_id].add(candidate)


class Migration(migrations.Migration):
    dependencies = [
        ('workplaces', '0004_workplace_code_workplace_description_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill_workplace_codes, migrations.RunPython.noop),
    ]
