"""Explicit React contracts; private files and all writes stay in domain views."""
from django.template.defaultfilters import date, filesizeformat
from django.utils import timezone

from core.frontend import form_payload


def dates(value):
    value = timezone.localtime(value)
    return {'date': date(value, 'd.m.Y'), 'datetime': date(value, 'd.m.Y, H:i')}


def file_variant(item):
    extension = item.extension.lower()
    groups = {
        'word': 'doc docx docm dot dotx dotm odt', 'excel': 'xls xlsx xlsm xlsb xlt xltx xltm csv tsv ods',
        'powerpoint': 'ppt pptx pptm pot potx pps ppsx ppsm odp', 'pdf': 'pdf',
        'image': 'jpg jpeg png gif webp svg bmp tif tiff heic avif',
        'archive': 'zip rar 7z tar gz bz2 xz tgz', 'audio': 'mp3 wav ogg flac m4a aac opus',
        'video': 'mp4 mov avi mkv webm m4v', 'code': 'json xml html css js ts py sql yaml yml',
        'board': 'board excalidraw', 'text': 'ancore txt rtf md log',
    }
    if getattr(item, 'kind', '') == 'board':
        return 'board'
    return next((key for key, extensions in groups.items() if extension in extensions.split()), 'text' if getattr(item, 'kind', '') == 'text' else 'generic')


def file_payload(item, base):
    result = {'id': str(item.pk), 'kind': getattr(item, 'kind', 'file'), 'name': item.title,
            'filename': item.filename, 'extension': item.extension, 'variant': file_variant(item),
            'size': filesizeformat(item.file_size), **dates(item.updated_at),
            'created': dates(item.created_at)['datetime'], 'deleted': dates(item.deleted_at)['date'] if item.deleted_at else '',
            'starred': item.is_starred, 'template': getattr(item, 'is_template', False),
            'office_type': item.office_type, 'full_editor': bool(getattr(item, 'has_full_editor', item.office_type)),
            'edit_url': f'{base}{item.pk}/', 'preview_url': f'{base}{item.pk}/preview/',
            'editor_url': f'{base}{item.pk}/editor/', 'download_url': f'{base}{item.pk}/download/',
            'star_url': f'{base}{item.pk}/star/', 'trash_url': f'{base}{item.pk}/trash/', 'restore_url': f'{base}{item.pk}/restore/',
            **({'move_url': f'{base}{item.pk}/move/'} if hasattr(item, 'library_id') else
               {'template_url': f'{base}{item.pk}/template/'} if item.office_type else {})}
    if item.deleted_at:
        for key in tuple(result):
            if key.endswith('_url') and key != 'restore_url':
                result[key] = ''
    return result


def library_payload(item, base):
    return {'id': str(item.pk), 'row_kind': 'library', 'name': item.name, 'color': item.color,
            'url': f'{base}?library={item.pk}', 'target': f'library:{item.pk}',
            'edit_url': f'{base}libraries/{item.pk}/edit/', 'delete_url': f'{base}libraries/{item.pk}/delete/',
            'size': filesizeformat(getattr(item, 'total_size', 0)), **dates(item.updated_at)}


def modal_payload(context):
    if not context:
        return None
    base = context['documents_url']
    form = context.get('form')
    schema = form_payload(form) if form is not None else None
    if schema:
        for field in schema['fields']:
            field['label_required'] = form.fields[field['name']].required
        schema['submit_label'] = context['submit_label']
    item = context.get('document')
    return {'title': context.get('form_title', item.title if item else ''), 'action': context['form_action'],
            'return_url': context['folder_url'], 'form': schema,
            'preview': context.get('preview'), 'content_url': context.get('content_url', ''),
            'document': file_payload(item, base) if item else None,
            'location': ' / '.join(filter(None, [getattr(context.get('current_library'), 'name', ''), getattr(context.get('current_folder'), 'name', '')])) or ('Dokumenty' if context.get('upload_form') else ''),
            'upload': bool(context.get('upload_form')), 'office_upload': bool(context.get('office_upload')),
            'create_editor': bool(context.get('office_create')), 'template_create': bool(context.get('template_create')),
            'has_templates': context.get('has_templates', True), 'max_size': filesizeformat(context.get('max_upload_size', 0)),
            'color_kind': 'library' if getattr(form, 'color_icon_template', '').endswith('drive_icon.html') else 'folder',
            'default_color': getattr(form, 'default_color', ''), 'preview_color': getattr(form, 'preview_color', ''),
            'convert_url': context.get('office_convert_url', ''), 'import_url': context.get('office_import_url', '')}


def form_page(request, context):
    data = modal_payload(context['modal'])
    return {'type': 'document-form', 'title': data['title'], 'data': data}


def directory_page(request, context):
    office = 'office_view' in context
    libraries = bool(context.get('is_library_index'))
    base = context['documents_url']
    rows = []
    if libraries:
        rows = [library_payload(item, base) for item in context['libraries']]
    else:
        for row in context['rows']:
            item = row['item']
            if row['kind'] == 'folder':
                data = {'id': str(item.pk), 'row_kind': 'folder', 'name': item.name, 'color': item.color,
                        'has_files': item.has_files, 'size': filesizeformat(item.total_size), **dates(item.created_at),
                        'starred': item.is_starred, 'target': f'folder:{item.pk}',
                        'move_url': f'{base}folders/{item.pk}/move/', 'edit_url': f'{base}folders/{item.pk}/edit/',
                        'delete_url': f'{base}folders/{item.pk}/delete/', 'star_url': f'{base}folders/{item.pk}/star/',
                        'download_url': f'{base}folders/{item.pk}/download/',
                        'location': f'folder:{item.parent_id}' if item.parent_id else f'library:{item.library_id}'}
            else:
                data = file_payload(item, base) | {'row_kind': 'document'}
                if not office:
                    data.update(location=f'folder:{item.folder_id}' if item.folder_id else f'library:{item.library_id}',
                                folder_name=item.folder.name if item.folder else '',
                                folder_url=f'{base}?library={item.library_id}&folder={item.folder_id}' if item.folder_id else '')
            if not office:
                data.update(library_name=item.library.name, library_url=f'{base}?library={item.library_id}')
            rows.append(data | {'url': '' if getattr(item, 'deleted_at', None) else row['url']})
    params = context['document_filter_params']
    values = {'return_query': context['return_query']} if office else {
        **params, 'scope': '' if context.get('current_library') else 'workspace',
        'view': context.get('library_view', ''), 'folder': str(getattr(context.get('current_folder'), 'pk', '') or ''),
        'q': context['query'], 'sort': context['sort'], 'page': str(context['document_window']['page']),
        'limit': str(context['document_window']['limit']), 'display': context['document_display'],
    }
    title = 'Dokumenty' if office else context['view_title']
    current_library = context.get('current_library')
    current_folder = context.get('current_folder')
    return {'type': 'document-directory', 'title': title, 'data': {
        'office': office, 'libraries': libraries, 'base_url': base, 'folder_url': context['folder_url'],
        'library': library_payload(current_library, base) if current_library else None,
        'folder': {'id': str(current_folder.pk), 'name': current_folder.name} if current_folder else None,
        'breadcrumbs': context.get('breadcrumbs', []), 'rows': rows,
        'sidebar': [library_payload(item, base) for item in context.get('sidebar_libraries', [])],
        'views': context['office_views'] if office else context['sidebar_views'],
        'view': context['office_view'] if office else context.get('library_view', ''),
        'display': context['document_display'], 'display_options': context['display_options'],
        'query': context['query'], 'filter_params': params,
        'filters': [{key: value for key, value in field.items() if key != 'lookup'} for field in context['document_filter_fields']],
        'operators': context['project_text_filter_operators'],
        'sort_fields': [{key: field[key] for key in ('value', 'label', 'icon', 'text') if key in field} for field in context['sort_fields']],
        'sort': context['sort'], 'sort_field': context['sort_field'], 'sort_direction': context['sort_direction'], 'sort_label': context['sort_label'],
        'active_filters': context['active_filter_count'], 'window': context['document_window'],
        'return_values': values, 'clear_url': context['clear_url'],
        'create_url': context.get('create_url', base + 'libraries/create/'), 'upload_url': context['upload_url'],
        'folder_create_url': context.get('folder_create_url', ''), 'template_create_url': context.get('template_create_url', ''),
        'modal': modal_payload(context.get('document_form')),
    }}


def text_page(request, context):
    item = context['document']
    return {'type': 'office-text', 'title': ('Nowy dokument' if context['is_new'] else item.title) + ' | Dokumenty', 'data': {
        'form': form_payload(context['form']), 'is_new': context['is_new'], 'back_url': context['folder_url'],
        'action': request.get_full_path(), 'document': None if context['is_new'] else file_payload(item, context['documents_url']),
        'upgrade_url': f'{context["documents_url"]}{item.pk}/upgrade/' if not context['is_new'] else '',
    }}


def suite_page(request, context):
    item = context['document']
    base = context['documents_url']
    return {'type': 'office-suite', 'title': item.title + (' | Dysk' if context['drive_editor'] else ' | Dokumenty'), 'data': {
        'document': file_payload(item, base), 'drive': context['drive_editor'], 'back_url': context['folder_url'],
        'revision': item.revision, 'save_receipt': context['office_save_receipt'],
        'rename_url': f'{base}{item.pk}/rename/', 'save_url': f'{base}{item.pk}/save/',
        'state_url': f'{base}{item.pk}/state/', 'board_url': f'{base}{item.pk}/board/' if getattr(item, 'kind', '') == 'board' else '',
        'editor_config': context.get('editor_config'), 'api_url': context['api_url'],
    }}
