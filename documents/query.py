"""Server-side query state for the shared directory filter/sort controls."""
from datetime import datetime, time, timedelta

from django.db.models import F, Q
from django.db.models.functions import Lower
from django.utils import timezone


TEXT_OPERATORS = (
    {'value': 'contains', 'label': 'zawiera'},
    {'value': 'not_contains', 'label': 'nie zawiera'},
    {'value': 'is_empty', 'label': 'jest puste'},
    {'value': 'is_not_empty', 'label': 'nie jest puste'},
)
DATE_OPTIONS = (
    {'value': 'today', 'label': 'Dzisiaj'},
    {'value': '7', 'label': 'Ostatnie 7 dni'},
    {'value': '30', 'label': 'Ostatnie 30 dni'},
)
PRESENCE_OPTIONS = (
    {'value': 'yes', 'label': 'Zawiera'},
    {'value': 'no', 'label': 'Nie zawiera'},
)
SIZE_OPTIONS = (
    {'value': 'small', 'label': 'Poniżej 1 MB'},
    {'value': 'medium', 'label': 'Od 1 do 5 MB'},
    {'value': 'large', 'label': 'Powyżej 5 MB'},
)
FILTER_PARAMETERS = (
    'name', 'name_op', 'filename', 'filename_op', 'description', 'description_op',
    'tag', 'document_library', 'file_type', 'starred', 'modified', 'size', 'documents', 'folders',
)
LIBRARY_SORT_FIELDS = (
    {'value': 'name', 'label': 'Nazwa dysku', 'icon': 'hard-drive', 'lookup': 'name', 'text': True},
    {'value': 'description', 'label': 'Opis', 'icon': 'align-left', 'lookup': 'description', 'text': True},
    {'value': 'documents', 'label': 'Liczba plików', 'icon': 'files', 'lookup': 'document_count'},
    {'value': 'folders', 'label': 'Liczba folderów', 'icon': 'folders', 'lookup': 'folder_count'},
    {'value': 'updated', 'label': 'Zmodyfikowano', 'icon': 'clock-3', 'lookup': 'updated_at'},
    {'value': 'created', 'label': 'Data utworzenia', 'icon': 'calendar-plus-2', 'lookup': 'created_at'},
)
DOCUMENT_SORT_FIELDS = (
    {'value': 'name', 'label': 'Nazwa pliku', 'icon': 'file-text', 'lookup': 'title', 'text': True},
    {'value': 'filename', 'label': 'Oryginalna nazwa pliku', 'icon': 'file', 'lookup': 'filename', 'text': True},
    {'value': 'description', 'label': 'Opis', 'icon': 'align-left', 'lookup': 'description', 'text': True},
    {'value': 'library', 'label': 'Dysk', 'icon': 'hard-drive', 'lookup': 'library__name', 'text': True},
    {'value': 'folder', 'label': 'Folder', 'icon': 'folder', 'lookup': 'folder__name', 'text': True},
    {'value': 'size', 'label': 'Rozmiar', 'icon': 'hard-drive', 'lookup': 'file_size'},
    {'value': 'updated', 'label': 'Zmodyfikowano', 'icon': 'clock-3', 'lookup': 'updated_at'},
    {'value': 'created', 'label': 'Data dodania', 'icon': 'calendar-plus-2', 'lookup': 'created_at'},
)


def text_field(params, key, label, icon, lookup):
    labels = {option['value']: option['label'] for option in TEXT_OPERATORS}
    operator = params.get(f'{key}_op', 'contains')
    operator = operator if operator in labels else 'contains'
    value = params.get(key, '').strip()[:255]
    empty_check = operator in {'is_empty', 'is_not_empty'}
    active = bool(value) or empty_check
    if empty_check:
        value = ''
    return {
        'kind': 'text', 'param': key, 'label': label, 'icon': icon, 'lookup': lookup,
        'value': value, 'operator': operator, 'operator_param': f'{key}_op', 'active': active,
        'value_label': (labels[operator] if empty_check else f'{labels[operator]} „{value}”') if active else '',
    }


def choice_field(params, key, label, icon, options, *, searchable=False):
    options = list(options)
    labels = {option['value']: option['label'] for option in options}
    value = params.get(key, '')
    value = value if value in labels else ''
    return {
        'kind': 'choice', 'param': key, 'label': label, 'icon': icon,
        'value': value, 'options': options, 'searchable': searchable,
        'active': bool(value), 'value_label': labels.get(value, ''), 'operator_param': '',
    }


def query_context(params, fields, sort_fields, default_sort):
    aliases = {'name': 'name_asc', 'updated': 'updated_desc', 'oldest': 'created_asc', 'size': 'size_desc'}
    sort = params.get('sort', '')
    sort = aliases.get(sort, sort)
    allowed_sorts = {f"{field['value']}_{direction}" for field in sort_fields for direction in ('asc', 'desc')}
    sort = sort if sort in allowed_sorts else default_sort
    field, _, direction = sort.rpartition('_')
    label = next(item['label'] for item in sort_fields if item['value'] == field)
    suffix = ('A–Z' if direction == 'asc' else 'Z–A') if field in {'name', 'filename', 'description', 'library', 'folder'} else ('rosnąco' if direction == 'asc' else 'malejąco')
    if field == 'name':
        label = 'Nazwa'
    inputs = {}
    for item in fields:
        inputs[item['param']] = item['value']
        if item['kind'] == 'text':
            inputs[item['operator_param']] = item['operator'] if item['active'] and item['operator'] != 'contains' else ''
    active = [item for item in fields if item['active']]
    return {
        'document_filter_fields': fields, 'document_filter_params': inputs,
        'document_active_filters': active, 'has_active_filters': bool(active),
        'active_filter_count': len(active), 'project_text_filter_operators': TEXT_OPERATORS,
        'sort_fields': sort_fields, 'sort': sort, 'sort_field': field, 'sort_direction': direction,
        'sort_param': sort if sort != default_sort else '', 'default_sort': default_sort,
        'sort_label': f'{label} {suffix}',
    }


def apply_text_filters(queryset, fields):
    for field in fields:
        if field['kind'] != 'text' or not field['active']:
            continue
        lookup, value, operator = field['lookup'], field['value'], field['operator']
        if operator in {'is_empty', 'is_not_empty'}:
            empty = Q(**{lookup: ''}) | Q(**{f'{lookup}__isnull': True})
            queryset = queryset.filter(empty) if operator == 'is_empty' else queryset.exclude(empty)
        elif value:
            match = {f'{lookup}__icontains': value}
            queryset = queryset.exclude(**match) if operator == 'not_contains' else queryset.filter(**match)
    return queryset


def apply_date_filter(queryset, lookup, value):
    if not value:
        return queryset
    days = 1 if value == 'today' else int(value)
    today = timezone.localdate()
    start = timezone.make_aware(datetime.combine(today - timedelta(days=days - 1), time.min))
    end = timezone.make_aware(datetime.combine(today + timedelta(days=1), time.min))
    return queryset.filter(**{f'{lookup}__gte': start, f'{lookup}__lt': end})


def order_results(queryset, context):
    field = next(item for item in context['sort_fields'] if item['value'] == context['sort_field'])
    expression = Lower(field['lookup']) if field.get('text') else F(field['lookup'])
    order = expression.desc(nulls_last=True) if context['sort_direction'] == 'desc' else expression.asc(nulls_last=True)
    return queryset.order_by(order, 'pk')
