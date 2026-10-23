"""Explicit data contracts for the existing saved-filter views and forms."""
from django.templatetags.static import static

from core.frontend import form_payload, pagination_payload
from spaces.frontend import item_payload


def filter_payload(item):
    return {
        'id': item.pk, 'name': item.name, 'description': item.description, 'query': item.query,
        'visibility': item.visibility, 'visibility_label': item.get_visibility_display(),
        'author': item.created_by.get_full_name() or item.created_by.email,
        'revision': item.revision, 'favorite': item.favorite, 'editable': item.editable,
        **{key: getattr(item, key) for key in ('url', 'edit_url', 'favorite_url', 'delete_url')},
    }


def filter_form_payload(form):
    schema = form_payload(form)
    schema.update(compact=False, layout='filter')
    return schema


def modal_payload(context):
    modal = context.get('modal')
    if not modal:
        return None
    return {'title': modal['title'], 'action': modal['action'], 'return_url': context['list_url'],
            'values': {'return_to': context['list_url']}, 'form': filter_form_payload(modal['form']),
            'filter_settings': 'edit' if modal['form'].instance.pk else 'create'}


def catalog_page(request, context):
    return {'type': 'filter-directory', 'title': 'Filtry', 'data': {
        **{key: context[key] for key in ('tab', 'query', 'filters_url', 'search_url', 'list_url')},
        'results': [filter_payload(item) for item in context['filters']],
        'pagination': pagination_payload(request, context['page'], context['filters_url']),
        'illustration': static('img/empty-states/filters-empty.webp'),
        'modal': modal_payload(context),
    }}


def search_page(request, context):
    item = context['saved_filter']
    return {'type': 'filter-search', 'title': item.name if item else 'Wyszukaj zadania', 'data': {
        **{key: context[key] for key in ('jql', 'search_error', 'mode', 'basic_available', 'changed',
            'search_url', 'filters_url', 'list_url', 'clear_url', 'save_as_url', 'basic_url', 'advanced_url', 'can_save')},
        'saved_filter': filter_payload(item) if item else None,
        'form': form_payload(context['search_form']),
        'items': [item_payload(item) for item in context['items']],
        'pagination': pagination_payload(request, context['page'], context['search_url']),
        'modal': modal_payload(context),
    }}
