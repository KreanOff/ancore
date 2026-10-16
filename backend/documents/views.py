from copy import copy
import mimetypes
import uuid
from urllib.parse import urlencode, urlsplit

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import BigIntegerField, Count, OuterRef, Q, Subquery, Sum
from django.db.models.functions import Coalesce
from django.db.models.deletion import RestrictedError
from django.http import FileResponse, Http404, JsonResponse, QueryDict
from django.shortcuts import get_object_or_404, redirect
from core.frontend import render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.views.decorators.clickjacking import xframe_options_sameorigin

from workplaces.services import workspace_owner

from core.upload_validation import ATTACHMENT_ALLOWED_EXTENSIONS, attachment_download_response
from workplaces.services import scoped_workplace_app_path
from .forms import DocumentForm, FolderForm, LibraryForm, UploadForm
from .folder_exports import folder_archive
from .folder_stats import set_folder_summaries
from .location_lock import location_write
from .models import Document, DocumentLibrary, Folder
from .previews import build_preview, inline_type, validate_inline
from .query import (
    DATE_OPTIONS, DOCUMENT_SORT_FIELDS, FILTER_PARAMETERS, LIBRARY_SORT_FIELDS,
    PRESENCE_OPTIONS, SIZE_OPTIONS, apply_date_filter, apply_text_filters,
    choice_field, order_results, query_context, text_field,
)


DOCUMENT_PAGE_SIZES = (10, 25, 50, 100, 150, 200)
DOCUMENT_VIEW_OPTIONS = (
    {'value': 'all', 'label': 'Wszystkie pliki', 'icon': 'files'},
    {'value': 'recent', 'label': 'Ostatnio zmienione', 'icon': 'clock-3'},
    {'value': 'starred', 'label': 'Oznaczone gwiazdką', 'icon': 'star'},
    {'value': 'trash', 'label': 'Kosz', 'icon': 'trash-2'},
)


def _url(request, suffix='', **params):
    base = scoped_workplace_app_path(request.workplace, 'documents', suffix)
    query = urlencode({key: value for key, value in params.items() if key != 'tag' and value not in ('', None)})
    return f'{base}?{query}' if query else base


def _documents(request):
    return Document.objects.filter(owner=workspace_owner(request), workplace=request.workplace)


def _folders(request):
    return Folder.objects.filter(owner=workspace_owner(request), workplace=request.workplace)


def _libraries(request):
    return DocumentLibrary.objects.filter(owner=workspace_owner(request), workplace=request.workplace)


def _by_id(queryset, value):
    try:
        return get_object_or_404(queryset, pk=int(value))
    except (ValueError, TypeError, OverflowError):
        raise Http404


def _folder(request, value):
    return _by_id(_folders(request), value) if value else None


def _location(request):
    folder = _folder(request, request.GET.get('folder'))
    library_id = request.GET.get('library') or (folder.library_id if folder else None)
    library = _by_id(_libraries(request), library_id)
    if folder and folder.library_id != library.pk:
        raise Http404
    return library, folder


def _context(request, library=None, folder=None):
    breadcrumbs = []
    ancestor = folder
    while ancestor:
        breadcrumbs.append({'name': ancestor.name, 'target': f'folder:{ancestor.pk}', 'url': _url(request, library=library.pk, folder=ancestor.pk)})
        ancestor = _folder(request, ancestor.parent_id)
    if library:
        breadcrumbs.append({'name': library.name, 'target': f'library:{library.pk}', 'url': _url(request, library=library.pk)})
    params = {'library': library.pk if library else None, 'folder': folder.pk if folder else None}
    return {
        'documents_url': _url(request), 'current_library': library, 'current_folder': folder,
        'breadcrumbs': list(reversed(breadcrumbs)), 'folder_url': _url(request, **params),
        'library_url': _url(request, library=library.pk) if library else _url(request),
        'upload_url': _url(request, 'upload/', **params),
        'folder_create_url': _url(request, 'folders/create/', **params),
    }



def _sidebar(request, active_view=None):
    counts = _documents(request).aggregate(
        all=Count('pk', filter=Q(deleted_at__isnull=True)),
        starred=Count('pk', filter=Q(deleted_at__isnull=True, is_starred=True)),
        trash=Count('pk', filter=Q(deleted_at__isnull=False)),
    )
    counts['starred'] += _folders(request).filter(library__in=_libraries(request), is_starred=True).count()
    return {
        'sidebar_libraries': _libraries(request).only('id', 'name', 'color', 'updated_at'),
        'sidebar_views': [
            {**option, 'url': _url(request, view=option['value']),
             'count': counts.get(option['value']), 'active': active_view == option['value']}
            for option in DOCUMENT_VIEW_OPTIONS
        ],
    }


def _display_context(request, scope):
    # Keep each account/Workspace and the library index independent in this session.
    key = f'documents_display:{request.user.pk}:{request.workplace.pk}:{scope}'
    display = request.GET.get('display')
    if display not in {'list', 'grid'}:
        display = request.session.get(key, 'list')
    if display not in {'list', 'grid'}:
        display = 'list'
    if request.session.get(key) != display:
        request.session[key] = display
    params = {name: request.GET[name] for name in (
        'library', 'folder', 'view', 'q', 'sort', 'page', 'page_size', *FILTER_PARAMETERS,
    ) if name in request.GET}
    return {
        'document_display': display,
        'display_options': [
            {'value': value, 'label': label, 'icon': icon, 'active': display == value,
             'url': _url(request, **{**params, 'display': value})}
            for value, label, icon in [('list', 'Lista', 'list'), ('grid', 'Kafelki', 'layout-grid')]
        ],
    }


def _pagination(request, total):
    try:
        page_size = int(request.GET.get('page_size', 50))
    except (ValueError, TypeError):
        page_size = 50
    if page_size not in DOCUMENT_PAGE_SIZES:
        page_size = 50
    page = Paginator(range(total), page_size).get_page(request.GET.get('page'))
    params = request.GET.copy()
    params.pop('page', None)
    params['page_size'] = page_size
    return page, {
        'page': page.number, 'total_pages': page.paginator.num_pages,
        'page_size': page_size, 'page_size_options': DOCUMENT_PAGE_SIZES,
        'has_previous': page.has_previous(), 'has_next': page.has_next(),
        'previous_url': _url(request, **{**params.dict(), 'page': page.previous_page_number()}) if page.has_previous() else '',
        'next_url': _url(request, **{**params.dict(), 'page': page.next_page_number()}) if page.has_next() else '',
        'compact_summary': f'{page.start_index()}–{page.end_index()} z {total}',
        'summary': f'Pokazano {page.start_index()}–{page.end_index()} z {total} elementów',
    }


def _library_index(request, form_context=None):
    query = request.GET.get('q', '').strip()[:120]
    fields = [
        text_field(request.GET, 'name', 'Nazwa dysku', 'hard-drive', 'name'),
        text_field(request.GET, 'description', 'Opis', 'align-left', 'description'),
        choice_field(request.GET, 'documents', 'Pliki', 'files', PRESENCE_OPTIONS),
        choice_field(request.GET, 'folders', 'Foldery', 'folders', PRESENCE_OPTIONS),
        choice_field(request.GET, 'modified', 'Zmodyfikowano', 'clock-3', DATE_OPTIONS),
    ]
    query_state = query_context(request.GET, fields, LIBRARY_SORT_FIELDS, 'name_asc')
    values = query_state['document_filter_params']
    library_sizes = _documents(request).filter(
        library_id=OuterRef('pk'), deleted_at__isnull=True,
    ).order_by().values('library_id').annotate(total=Sum('file_size')).values('total')
    libraries = _libraries(request).filter(Q(name__icontains=query) | Q(description__icontains=query)).annotate(
        document_count=Count('documents', filter=Q(documents__deleted_at__isnull=True, documents__owner=workspace_owner(request), documents__workplace=request.workplace), distinct=True),
        folder_count=Count('folders', filter=Q(folders__owner=workspace_owner(request), folders__workplace=request.workplace), distinct=True),
        total_size=Coalesce(Subquery(library_sizes), 0, output_field=BigIntegerField()),
    )
    libraries = apply_text_filters(libraries, fields)
    for param, count in [('documents', 'document_count'), ('folders', 'folder_count')]:
        if values[param]:
            lookup = count if values[param] == 'no' else f'{count}__gt'
            libraries = libraries.filter(**{lookup: 0})
    libraries = apply_date_filter(libraries, 'updated_at', values['modified'])
    libraries = order_results(libraries, query_state)
    page, window = _pagination(request, libraries.count())
    start = page.start_index() - 1 if page.paginator.count else 0
    context = _context(request)
    context.update(_sidebar(request))
    context.update(_display_context(request, 'libraries'))
    context.update(query_state)
    context.update({
        'is_library_index': True, 'view_title': 'Dyski', 'document_form': form_context,
        'libraries': libraries[start:page.end_index()], 'page': page, 'document_window': window,
        'query': query, 'clear_url': _url(request),
    })
    return render(request, 'documents/libraries.html', context)


@login_required
@require_GET
def library(request):
    return _library_page(request)


def _library_page(request, form_context=None):
    if not request.GET.get('library'):
        # Keep saved links to existing folders working after introducing libraries.
        folder = _folder(request, request.GET.get('folder'))
        if folder:
            return redirect(_url(request, **{**request.GET.dict(), 'library': folder.library_id}))
        if not request.GET.get('view'):
            return _library_index(request, form_context)
        current_library, folder = None, None
    else:
        current_library, folder = _location(request)
    current_view = request.GET.get('view', 'all')
    if current_view not in {'all', 'recent', 'starred', 'trash'}:
        current_view = 'all'
    query = request.GET.get('q', '').strip()[:120]
    selected_library = None
    if not current_library and request.GET.get('document_library'):
        selected_library = _by_id(_libraries(request), request.GET['document_library'])
    fields = [
        text_field(request.GET, 'name', 'Nazwa pliku', 'file-text', 'title'),
        text_field(request.GET, 'filename', 'Oryginalna nazwa pliku', 'file', 'filename'),
        text_field(request.GET, 'description', 'Opis', 'align-left', 'description'),
        choice_field(request.GET, 'file_type', 'Typ pliku', 'file-type', (
            {'value': extension, 'label': extension[1:].upper()} for extension in sorted(ATTACHMENT_ALLOWED_EXTENSIONS)
        ), searchable=True),
        choice_field(request.GET, 'size', 'Rozmiar', 'hard-drive', SIZE_OPTIONS),
        choice_field(request.GET, 'starred', 'Gwiazdka', 'star', (
            {'value': 'yes', 'label': 'Oznaczone gwiazdką'}, {'value': 'no', 'label': 'Bez gwiazdki'},
        )),
        choice_field(request.GET, 'modified', 'Usunięto' if current_view == 'trash' else 'Zmodyfikowano', 'clock-3', DATE_OPTIONS),
    ]
    if not current_library:
        fields.insert(3, choice_field(request.GET, 'document_library', 'Dysk', 'hard-drive', (
            {'value': str(item.pk), 'label': item.name} for item in _libraries(request)
        ), searchable=True))
    sort_fields = tuple(
        {**field, 'label': 'Usunięto', 'lookup': 'deleted_at'}
        if current_view == 'trash' and field['value'] == 'updated' else field
        for field in DOCUMENT_SORT_FIELDS
    )
    query_state = query_context(request.GET, fields, sort_fields, 'updated_desc')
    values = query_state['document_filter_params']
    # Searching/filtering spans nested folders within the current library.
    searching = bool(query or query_state['has_active_filters'])
    document_only_filter = any(field['active'] and field['param'] not in {'name', 'modified', 'starred', 'document_library'} for field in fields)
    documents = _documents(request).filter(deleted_at__isnull=current_view != 'trash')
    if current_library:
        documents = documents.filter(library=current_library)
    elif selected_library:
        documents = documents.filter(library=selected_library)
    # Workspace-wide file views include folders for stars, without changing "All files".
    show_folders = current_library or current_view == 'starred' or values['starred']
    folders = _folders(request).filter(library__in=_libraries(request)) if show_folders and current_view in {'all', 'starred'} and not document_only_filter else Folder.objects.none()
    if current_library or selected_library:
        folders = folders.filter(library=current_library or selected_library)
    if not searching and current_library and current_view == 'all':
        folders = folders.filter(parent=folder)
    if current_view == 'starred':
        documents = documents.filter(is_starred=True)
        folders = folders.filter(is_starred=True)
    if query:
        documents = documents.filter(Q(title__icontains=query) | Q(filename__icontains=query) | Q(description__icontains=query)).distinct()
        folders = folders.filter(name__icontains=query)
    elif current_library and current_view == 'all' and not searching:
        documents = documents.filter(folder=folder)
    documents = apply_text_filters(documents, fields)
    folders = apply_text_filters(folders, [{**field, 'lookup': 'name'} for field in fields if field['param'] == 'name'])
    documents = apply_date_filter(documents, 'deleted_at' if current_view == 'trash' else 'updated_at', values['modified'])
    folders = apply_date_filter(folders, 'created_at', values['modified'])
    if values['file_type']:
        documents = documents.filter(filename__iendswith=values['file_type'])
    if values['starred']:
        documents = documents.filter(is_starred=values['starred'] == 'yes')
        folders = folders.filter(is_starred=values['starred'] == 'yes')
    if values['size'] == 'small':
        documents = documents.filter(file_size__lt=1024 * 1024)
    elif values['size'] == 'medium':
        documents = documents.filter(file_size__gte=1024 * 1024, file_size__lte=5 * 1024 * 1024)
    elif values['size'] == 'large':
        documents = documents.filter(file_size__gt=5 * 1024 * 1024)
    documents = order_results(documents.select_related('folder', 'owner', 'library'), query_state)
    folder_sort = query_state['sort_field'] if query_state['sort_field'] in {'name', 'updated', 'created'} else 'name'
    folder_sort_fields = (
        {'value': 'name', 'lookup': 'name', 'text': True},
        {'value': 'updated', 'lookup': 'created_at'}, {'value': 'created', 'lookup': 'created_at'},
    )
    folders = order_results(folders.select_related('library'), {**query_state, 'sort_fields': folder_sort_fields, 'sort_field': folder_sort})
    folder_count = folders.count()
    page, window = _pagination(request, folder_count + documents.count())
    start, end = (page.start_index() - 1 if page.paginator.count else 0), page.end_index()
    rows = [
        {'kind': 'folder', 'item': item, 'url': _url(request, library=item.library_id, folder=item.pk)}
        for item in folders[start:end]
    ] if start < folder_count else []
    set_folder_summaries(rows, _folders(request), _documents(request), library_scoped=True)
    if end > folder_count:
        rows += [
            {'kind': 'document', 'item': item, 'url': _url(request, f'{item.pk}/editor/' if item.office_type else f'{item.pk}/preview/')}
            for item in documents[max(0, start - folder_count):end - folder_count]
        ]
    library_id = current_library.pk if current_library else None
    view_label = next(option['label'] for option in DOCUMENT_VIEW_OPTIONS if option['value'] == current_view)
    context = _context(request, current_library, folder)
    context.update(_sidebar(request, active_view=current_view if not current_library else None))
    context.update(_display_context(request, 'files'))
    context.update(query_state)
    context.update({
        'clear_url': _url(request, library=library_id, view=current_view, folder=folder.pk if folder else None),
        'view_url': _url(request, library=library_id, view=current_view, folder=folder.pk if folder else None),
        'rows': rows, 'page': page, 'query': query, 'document_window': window, 'document_form': form_context,
        'library_view': current_view,
        'view_label': view_label,
        'view_title': (folder.name if folder and not searching and current_view == 'all' else current_library.name) if current_library else view_label,
    })
    return render(request, 'documents/library.html', context)


def _render_form(request, context, template='documents/form.html'):
    context['form_action'] = request.get_full_path()
    if getattr(request, '_react_api', False):
        invalid = context.get('form') is not None and context['form'].is_bound and context['form'].errors
        return render(request, template, {'modal': context}, status=400 if invalid else 200)
    if request.headers.get('X-Document-Modal') == 'true':
        return render(request, template, {'modal': context})
    # Direct links and ordinary form submissions use the same dialog over its list.
    background_request = copy(request)
    background_request.GET = QueryDict(urlsplit(context['folder_url']).query)
    return _library_page(background_request, context)


def _form_success(request, url):
    if request.headers.get('X-Document-Modal') == 'true':
        return JsonResponse({'redirect_url': url})
    return redirect(url)


def _save_library(request, instance=None):
    form = LibraryForm(request.POST if request.method == 'POST' else None,
                       instance=instance, owner=workspace_owner(request), workplace=request.workplace)
    if request.method == 'POST' and form.is_valid():
        item = form.save(commit=False)
        item.owner, item.workplace = workspace_owner(request), request.workplace
        try:
            with transaction.atomic():
                item.save()
        except IntegrityError:
            form.add_error('name', 'Dysk o tej nazwie już istnieje w tym Workspace.')
        else:
            messages.success(request, 'Zapisano dysk.' if instance else 'Utworzono dysk.')
            return _form_success(request, _url(request, library=item.pk))
    context = _context(request, instance)
    context.update({'form': form,
                    'form_title': 'Ustawienia dysku' if instance else 'Nowy dysk',
                    'submit_label': 'Zapisz dysk' if instance else 'Utwórz dysk'})
    return _render_form(request, context)


@login_required
@require_http_methods(['GET', 'POST'])
def library_create(request):
    return _save_library(request)


@login_required
@require_http_methods(['GET', 'POST'])
def library_edit(request, pk):
    return _save_library(request, get_object_or_404(_libraries(request), pk=pk))


@login_required
@require_GET
def library_photo(request, pk):
    library = get_object_or_404(_libraries(request), pk=pk)
    if not library.photo:
        raise Http404
    try:
        photo = library.photo.open('rb')
    except FileNotFoundError:
        raise Http404
    response = FileResponse(photo, content_type=mimetypes.guess_type(library.photo.name)[0] or 'application/octet-stream')
    response['Cache-Control'] = 'private, no-store'
    response['X-Content-Type-Options'] = 'nosniff'
    return response


@login_required
@require_POST
@location_write
def library_delete(request, pk):
    item = get_object_or_404(_libraries(request), pk=pk)
    try:
        item.delete()
    except RestrictedError:
        messages.error(request, 'Można usunąć tylko pusty dysk. Zawiera on foldery lub pliki, również w koszu.')
    else:
        messages.success(request, 'Usunięto pusty dysk.')
    return redirect(_url(request))


@login_required
@require_http_methods(['GET', 'POST'])
@location_write
def upload(request):
    current_library, folder = _location(request)
    form = UploadForm(request.POST if request.method == 'POST' else None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        saved_files = []
        try:
            with transaction.atomic():
                for file in form.cleaned_data['files']:
                    document = Document(owner=workspace_owner(request), workplace=request.workplace, library=current_library, folder=folder,
                                        title=file.name, filename=file.name, file_size=file.size)
                    document.file.save(file.name, file, save=False)
                    saved_files.append((document.file.storage, document.file.name))
                    document.save()
        except Exception:
            for storage, name in saved_files:
                storage.delete(name)
            raise
        messages.success(request, f'Przesłano pliki: {len(saved_files)}.')
        return _form_success(request, _url(request, library=current_library.pk, folder=folder.pk if folder else None))
    context = _context(request, current_library, folder)
    context.update({'form': form, 'form_title': 'Prześlij pliki', 'submit_label': 'Prześlij pliki',
                    'upload_form': True, 'max_upload_size': settings.MAX_ATTACHMENT_SIZE})
    return _render_form(request, context)


def _save_folder(request, folder=None):
    if folder:
        current_library, parent = folder.library, _folder(request, folder.parent_id)
    else:
        current_library, parent = _location(request)
    form = FolderForm(request.POST if request.method == 'POST' else None, instance=folder, owner=workspace_owner(request), workplace=request.workplace, library=current_library, parent=parent)
    if request.method == 'POST' and form.is_valid():
        item = form.save(commit=False)
        item.owner, item.workplace, item.parent, item.library = workspace_owner(request), request.workplace, parent, current_library
        try:
            with transaction.atomic():
                item.save()
        except IntegrityError:
            form.add_error('name', 'Folder o tej nazwie już istnieje w tym miejscu.')
        else:
            messages.success(request, 'Zapisano folder.' if folder else 'Utworzono folder.')
            return _form_success(request, _url(request, library=current_library.pk, folder=parent.pk if parent else None))
    context = _context(request, current_library, parent)
    context.update({'form': form, 'form_title': 'Edytuj folder' if folder else 'Nowy folder', 'submit_label': 'Zapisz folder'})
    return _render_form(request, context)


@login_required
@require_http_methods(['GET', 'POST'])
@location_write
def folder_create(request):
    return _save_folder(request)


@login_required
@require_http_methods(['GET', 'POST'])
@location_write
def folder_edit(request, pk):
    return _save_folder(request, get_object_or_404(_folders(request).select_related('library'), pk=pk))


@login_required
@require_POST
@location_write
def folder_delete(request, pk):
    folder = get_object_or_404(_folders(request), pk=pk)
    parent_id, library_id = folder.parent_id, folder.library_id
    try:
        folder.delete()
    except RestrictedError:
        messages.error(request, 'Folder zawiera podfoldery lub pliki (również w koszu). Najpierw je przenieś.')
    else:
        messages.success(request, 'Usunięto pusty folder.')
    return redirect(_url(request, library=library_id, folder=parent_id))


@login_required
@require_POST
def folder_star(request, pk):
    with transaction.atomic():
        folder = get_object_or_404(_folders(request).filter(library__in=_libraries(request)).select_for_update(), pk=pk)
        folder.is_starred = not folder.is_starred
        folder.save(update_fields=['is_starred'])
    return _return_to_library(request, folder)


@login_required
@require_GET
def folder_download(request, pk):
    folder = get_object_or_404(_folders(request).filter(library__in=_libraries(request)), pk=pk)
    try:
        archive, filename = folder_archive(
            folder, _folders(request).filter(library_id=folder.library_id),
            _documents(request).filter(library_id=folder.library_id, deleted_at__isnull=True),
        )
    except OSError:
        raise Http404('Nie można pobrać folderu. Jeden z plików nie jest dostępny.')
    response = FileResponse(archive, as_attachment=True, filename=filename, content_type='application/zip')
    response['Cache-Control'] = 'private, no-store'
    response['X-Content-Type-Options'] = 'nosniff'
    return response


@login_required
@require_http_methods(['GET', 'POST'])
@location_write
def detail(request, pk):
    document = get_object_or_404(_documents(request).select_related('folder', 'library'), pk=pk, deleted_at__isnull=True)
    form = DocumentForm(request.POST if request.method == 'POST' else None, instance=document, owner=workspace_owner(request), workplace=request.workplace)
    if request.method == 'POST' and form.is_valid():
        # Metadata edits must not overwrite a file/revision saved by the editor.
        with transaction.atomic():
            locked = get_object_or_404(_documents(request).select_for_update(), pk=pk, deleted_at__isnull=True)
            for field in ('title', 'description', 'folder'):
                setattr(locked, field, form.cleaned_data[field])
            locked.save(update_fields=['title', 'description', 'folder', 'updated_at'])
        messages.success(request, 'Zapisano plik.')
        return _form_success(request, _url(request, library=document.library_id, folder=form.instance.folder_id))
    context = _context(request, document.library, document.folder)
    context.update({'form': form, 'document': document, 'form_title': document.title, 'submit_label': 'Zapisz zmiany'})
    return _render_form(request, context)


@login_required
@require_GET
def preview(request, pk):
    document = get_object_or_404(_documents(request).select_related('folder', 'library'), pk=pk, deleted_at__isnull=True)
    if document.office_type:
        return redirect(_url(request, f'{pk}/editor/'))
    context = _context(request, document.library, document.folder)
    context.update({'document': document, 'preview': build_preview(document),
                    'content_url': _url(request, f'{document.pk}/content/')})
    from .office_service import LEGACY_FORMATS, configured
    if document.extension in LEGACY_FORMATS and configured():
        context['office_convert_url'] = _url(request, f'{pk}/convert/')
    response = _render_form(request, context, template='documents/preview.html')
    response['Cache-Control'] = 'private, no-store'
    return response


@login_required
@require_GET
@xframe_options_sameorigin
def preview_content(request, pk):
    document = get_object_or_404(_documents(request), pk=pk, deleted_at__isnull=True)
    kind = inline_type(document)
    if not kind or not document.file:
        raise Http404
    try:
        file = document.file.open('rb')
    except OSError:
        raise Http404('Plik nie jest dostępny.')
    try:
        validate_inline(file, document.filename)
        response = FileResponse(file, as_attachment=False, filename=document.filename, content_type=kind[1])
    except (OSError, ValueError):
        file.close()
        raise Http404('Plik nie jest dostępny.')
    response['Cache-Control'] = 'private, no-store'
    response['X-Content-Type-Options'] = 'nosniff'
    response['Content-Security-Policy'] = "sandbox; default-src 'none'; frame-ancestors 'self'"
    return response


@login_required
@require_GET
def download(request, pk):
    document = get_object_or_404(_documents(request), pk=pk, deleted_at__isnull=True)
    try:
        response = attachment_download_response(document)
    except FileNotFoundError:
        raise Http404('Plik nie jest dostępny.')
    response['Cache-Control'] = 'private, no-store'
    return response


def _return_to_library(request, document):
    params = {key: request.POST.get(key, '') for key in dict.fromkeys(('view', 'folder', 'q', 'sort', 'page', 'page_size', *FILTER_PARAMETERS))}
    if request.POST.get('display') in {'list', 'grid'}:
        params['display'] = request.POST['display']
    library_id = None if request.POST.get('scope') == 'workspace' else document.library_id
    if library_id is None:
        params['view'] = params['view'] or 'all'
        params.pop('folder', None)
    return redirect(_url(request, library=library_id, **params))


@login_required
@require_POST
def star(request, pk):
    with transaction.atomic():
        document = get_object_or_404(_documents(request).select_for_update(), pk=pk, deleted_at__isnull=True)
        document.is_starred = not document.is_starred
        document.save(update_fields=['is_starred'])
    return _return_to_library(request, document)


@login_required
@require_POST
def trash(request, pk):
    with transaction.atomic():
        document = get_object_or_404(_documents(request).select_for_update(), pk=pk, deleted_at__isnull=True)
        document.deleted_at, document.office_key = timezone.now(), uuid.uuid4()
        document.save(update_fields=['deleted_at', 'office_key'])
    messages.success(request, 'Plik przeniesiono do kosza. Możesz go przywrócić.')
    return _return_to_library(request, document)


@login_required
@require_POST
def restore(request, pk):
    with transaction.atomic():
        document = get_object_or_404(_documents(request).select_for_update(), pk=pk, deleted_at__isnull=False)
        document.deleted_at, document.office_key = None, uuid.uuid4()
        document.save(update_fields=['deleted_at', 'office_key'])
    messages.success(request, 'Przywrócono plik do jego folderu.')
    return _return_to_library(request, document)
