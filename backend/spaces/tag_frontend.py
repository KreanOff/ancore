"""Space-scoped tag directory; all mutations still use tasks.tagging.tag_action."""
from core.frontend import form_payload
from django.db.models import Prefetch, prefetch_related_objects
from tasks.models import TaskTagNote
from .frontend import space_payload


def tag_form_payload(form, editing=False):
    schema = form_payload(form)
    schema['layout'] = 'tag'
    schema['submit_label'] = 'Zapisz zmiany' if editing else 'Utwórz tag'
    for field in schema['fields']:
        if field['name'] == 'name':
            field['label'] = 'Nazwa tagu'
        elif field['name'] == 'description':
            field['label'] = 'Opis'
    return schema


def tags_page(request, context):
    space, window = context['space'], context['tag_window']
    space.url = context['space_url']
    tags = context['tags']
    prefetch_related_objects(tags, Prefetch('tag_notes', queryset=TaskTagNote.objects.select_related('author')))
    # Only related tags in this Space may appear, including in imported data.
    for tag in tags:
        tag._react_related = [related for related in tag.related_tags.all()
                              if (related.space_id, related.user_id, related.workplace_id) ==
                              (space.pk, space.user_id, request.workplace.pk)]
    return {'type': 'space-tags', 'title': f'{space.name} · Tagi', 'data': {
        'space': space_payload(space), 'navigation': context['navigation'], 'can_edit': context['can_edit_tags'],
        'form': tag_form_payload(context['tag_form']) if context['can_edit_tags'] else None,
        'modal': {'title': 'Edytuj tag' if context.get('tag_edit_mode') else 'Nowy tag',
                  'action': request.get_full_path(), 'return_url': request.get_full_path(),
                  'values': {'action': 'edit_tag' if context.get('tag_edit_mode') else 'create_tag',
                             'tag_id': str(context.get('tag_edit_tag_id', ''))},
                  'form': tag_form_payload(context['tag_form'], context.get('tag_edit_mode', False))} if context.get('tag_modal_open') else None,
        'tags': [{
            'id': tag.pk, 'name': tag.name, 'code': tag.code, 'description': tag.description,
            **{key: getattr(tag, key) for key in ('category', 'color', 'icon', 'priority', 'scope',
                'owner_label', 'status', 'usage_notes', 'automation_rules', 'created_at')},
            'labels': {key: getattr(tag, f'get_{key}_display')() for key in ('category', 'icon', 'priority', 'scope', 'status')},
            'related_tags': [str(related.pk) for related in tag._react_related],
            'related_label': ', '.join(related.name for related in tag._react_related) or 'Brak powiązań',
            'task_count': tag.total_tasks,
            'notes': [{'id': note.pk, 'message': note.message, 'created_at': note.created_at, 'edited_at': note.edited_at,
                       'author': (note.author.get_full_name() or note.author.username) if note.author else 'System',
                       'editable': context['can_edit_tags'] and note.author_id == request.user.pk}
                      for note in tag.tag_notes.all()],
        } for tag in tags],
        'query': window['query'], 'filters': {key: window[key] for key in ('priority', 'status', 'category', 'scope', 'owner')},
        'filter_options': window['filters'], 'sort': window['sort'], 'sort_options': context['tag_sort_options'],
        'window': {key: value for key, value in window.items() if key in {
            'page', 'total_pages', 'total_tags', 'page_size', 'page_size_options', 'page_items',
            'previous_url', 'next_url', 'summary', 'compact_summary'}},
    }}
