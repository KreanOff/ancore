"""Display ordering, shared by task pages and bulk planning validation."""
from django.db.models import Case, F, IntegerField, Value, When
from django.db.models.functions import Lower


SORT_FIELDS = [
    {'value': 'rank', 'label': 'Kolejność ręczna', 'icon': 'list-ordered'},
    {'value': 'number', 'label': 'Klucz zadania', 'icon': 'hash'},
    {'value': 'title', 'label': 'Tytuł', 'icon': 'align-left'},
    {'value': 'priority', 'label': 'Priorytet', 'icon': 'flag'},
    {'value': 'due', 'label': 'Termin', 'icon': 'calendar-days'},
    {'value': 'created', 'label': 'Data utworzenia', 'icon': 'clock'},
    {'value': 'start', 'label': 'Data rozpoczęcia', 'icon': 'calendar-range'},
    {'value': 'points', 'label': 'Punkty', 'icon': 'target'},
]


def item_sort(request, view='list'):
    default = 'start_asc' if view == 'timeline' else 'rank_asc'
    value = request.GET.get('sort', default)
    if value not in {f"{field['value']}_{direction}" for field in SORT_FIELDS for direction in ('asc', 'desc')}:
        value = default
    field, direction = value.rsplit('_', 1)
    return {'value': value, 'field': field, 'direction': direction, 'fields': SORT_FIELDS,
            'label': next(row['label'] for row in SORT_FIELDS if row['value'] == field),
            'manual': value == 'rank_asc', 'default': default}


def order_items(request, items, view='list'):
    sort = item_sort(request, view)
    expressions = {
        'rank': F('rank'), 'number': F('number'), 'title': Lower('task__title'),
        'priority': Case(*[When(task__priority=key, then=Value(index))
                           for index, key in enumerate(('none', 'low', 'medium', 'high', 'urgent'))],
                         default=Value(0), output_field=IntegerField()),
        'due': F('task__due_at'), 'created': F('task__created_at'),
        'start': F('start_at'), 'points': F('points'),
    }
    expression = expressions[sort['field']]
    order = expression.desc(nulls_last=True) if sort['direction'] == 'desc' else expression.asc(nulls_last=True)
    return items.order_by(order, *(['task__due_at'] if sort['field'] == 'start' else []), 'pk')
