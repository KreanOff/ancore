"""Typed contracts for saved/default dashboards; domain views retain all writes."""
from django.templatetags.static import static
from django.utils.html import strip_tags

from core.frontend import form_payload, pagination_payload


def dashboard_payload(item):
    return {
        'id': item.pk, 'slug': item.slug, 'name': item.name, 'description': item.description,
        'author': item.created_by.get_full_name() or item.created_by.email,
        'visibility': item.visibility, 'visibility_label': item.get_visibility_display(),
        'layout': item.layout, 'revision': item.revision, 'is_default': item.is_default,
        'editable': item.can_edit, 'favorite': item.is_favorite,
        'gadget_count': getattr(item, 'gadget_count', 0),
        **{key: getattr(item, key) for key in ('url', 'edit_url', 'access_url', 'gadgets_url', 'delete_url', 'favorite_url')},
    }


def gadget_payload(data, editable=False):
    gadget = data['gadget']
    result = {'id': gadget.pk, 'kind': gadget.kind, 'label': gadget.label, 'icon': gadget.icon,
              'edit_url': gadget.edit_url if editable else '', 'delete_url': gadget.delete_url if editable else '',
              'unavailable': data['unavailable']}
    if not data['unavailable']:
        result.update({key: data[key] for key in ('count', 'closed_count', 'percent', 'statuses', 'caption')})
    return result


def pulpit_form_payload(form):
    result = form_payload(form)
    result.update(layout='pulpit', compact=True)
    for field in result['fields']:
        field['label_required'] = form.fields[field['name']].required
        if field['name'] == 'layout':
            for choice in field['choices']:
                choice['layout_preview'] = choice['value']
    if getattr(form, 'catalog', None):
        result['gadget_catalog'] = form.catalog
        result['illustration'] = static('img/empty-states/dashboard-empty.webp')
    return result


def modal_payload(context):
    modal = context.get('modal')
    if not modal:
        return None
    return {key: modal[key] for key in ('title', 'action', 'return_url')} | {'form': pulpit_form_payload(modal['form'])}


def directory_page(request, context):
    management = 'management_url' in context
    base = context['management_url'] if management else context['dashboards_url']
    return {'type': 'pulpit-directory', 'title': 'Zarządzaj pulpitami' if management else 'Pulpity', 'data': {
        'management': management, 'base_url': base, 'query': context['query'],
        'visibility': context['visibility_filter'], 'favorite': context.get('favorite_filter', ''),
        'visibility_choices': context['visibility_choices'], 'create_url': context['create_url'],
        'list_url': context.get('return_url', request.get_full_path()),
        'results': [dashboard_payload(item) | {'description': strip_tags(item.description)} for item in (context['page'] if management else context['dashboards'])],
        'pagination': pagination_payload(request, context['page'], base),
        'illustration': static('img/empty-states/dashboard-empty.webp'), 'modal': modal_payload(context),
    }}


def detail_page(request, context):
    dashboard = context['dashboard']
    editing = bool(context.get('editing_gadgets'))
    return {'type': 'pulpit-detail', 'title': dashboard.name, 'data': {
        'dashboard': dashboard_payload(dashboard), 'editing': editing,
        'columns': [[gadget_payload(data, editable=editing) for data in column] for column in context['columns']],
        'layout_choices': context['layout_choices'], 'add_gadget_url': context['add_gadget_url'],
        'arrange_url': context['arrange_url'], 'quick_add_url': context.get('quick_add_url', ''),
        'editor_url': context.get('editor_url', dashboard.gadgets_url), 'return_url': context.get('return_url', dashboard.url),
        'list_url': context.get('editor_url', dashboard.url),
        'max_gadgets': context.get('max_gadgets', 0), 'gadget_catalog': context.get('gadget_catalog', []),
        'illustration': static('img/empty-states/dashboard-empty.webp'),
        'column_illustration': static('img/empty-states/gadget-column-empty.webp'),
        'modal': modal_payload(context),
    }}


def edit_page(request, context):
    dashboard = context['dashboard']
    return {'type': 'pulpit-edit', 'title': f'{context["section_title"]} — {dashboard.name}', 'data': {
        'dashboard': dashboard_payload(dashboard), 'section': next(row['key'] for row in context['pulpit_editor_navigation'] if row['active']),
        'form': pulpit_form_payload(context['form']), 'action': context['action'], 'return_url': context['return_url'],
    }}
