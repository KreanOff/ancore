from copy import copy
from urllib.parse import urlencode, urlsplit

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.db.models.deletion import RestrictedError
from django.http import Http404, JsonResponse, QueryDict
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from core.upload_validation import ATTACHMENT_ALLOWED_EXTENSIONS, attachment_download_response
from tasks.models import TaskTag
from workplaces.services import scoped_workplace_app_path
from .forms import DocumentForm, FolderForm, LibraryForm, UploadForm
from .models import Document, DocumentLibrary, Folder
from .query import (
    DATE_OPTIONS, DOCUMENT_SORT_FIELDS, FILTER_PARAMETERS, LIBRARY_SORT_FIELDS,
    PRESENCE_OPTIONS, SIZE_OPTIONS, apply_date_filter, apply_text_filters,
    choice_field, order_results, query_context, text_field,
)


DOCUMENT_PAGE_SIZES = (10, 25, 50, 100, 150, 200)
DOCUMENT_VIEW_OPTIONS = (
    {'value': 'all', 'label': 'Wszystkie dokumenty', 'icon': 'files'},
    {'value': 'recent', 'label': 'Ostatnio zmienione', 'icon': 'clock-3'},
    {'value': 'starred', 'label': 'Oznaczone gwiazdką', 'icon': 'star'},
    {'value': 'trash', 'label': 'Kosz', 'icon': 'trash-2'},
)


def _url(request, suffix='', **params):
    base = scoped_workplace_app_path(request.workplace, 'documents', suffix)
    query = urlencode({key: value for key, value in params.items() if value not in ('', None)})
    return f'{base}?{query}' if query else base


def _documents(request):
    return Document.objects.filter(owner=request.user, workplace=request.workplace)


def _folders(request):
    return Folder.objects.filter(owner=request.user, workplace=request.workplace)


def _libraries(request):
    return DocumentLibrary.objects.filter(owner=request.user, workplace=request.workplace)


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
        breadcrumbs.append({'name': ancestor.name, 'url': _url(request, library=library.pk, folder=ancestor.pk)})
        ancestor = _folder(request, ancestor.parent_id)
    if library:
        breadcrumbs.append({'name': library.name, 'url': _url(request, library=library.pk)})
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
    return {
        'sidebar_libraries': _libraries(request).only('id', 'name'),
        'sidebar_views': [
            {**option, 'url': _url(request, view=option['value']),
             'count': counts.get(option['value']), 'active': active_view == option['value']}
            for option in DOCUMENT_VIEW_OPTIONS
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
        text_field(request.GET, 'name', 'Nazwa biblioteki', 'library-big', 'name'),
        text_field(request.GET, 'description', 'Opis', 'align-left', 'description'),
        choice_field(request.GET, 'documents', 'Pliki', 'files', PRESENCE_OPTIONS),
        choice_field(request.GET, 'folders', 'Foldery', 'folders', PRESENCE_OPTIONS),
        choice_field(request.GET, 'modified', 'Zmodyfikowano', 'clock-3', DATE_OPTIONS),
    ]
    query_state = query_context(request.GET, fields, LIBRARY_SORT_FIELDS, 'name_asc')
    values = query_state['document_filter_params']
    libraries = _libraries(request).filter(Q(name__icontains=query) | Q(description__icontains=query)).annotate(
        document_count=Count('documents', filter=Q(documents__deleted_at__isnull=True, documents__owner=request.user, documents__workplace=request.workplace), distinct=True),
        folder_count=Count('folders', filter=Q(folders__owner=request.user, folders__workplace=request.workplace), distinct=True),
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
    context.update(query_state)
    context.update({
        'is_library_index': True, 'view_title': 'Biblioteki dokumentów', 'document_form': form_context,
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
    tags = TaskTag.objects.filter(user=request.user, workplace=request.workplace)
    selected_tag = _by_id(tags, request.GET['tag']) if request.GET.get('tag') else None
    selected_library = None
    if not current_library and request.GET.get('document_library'):
        selected_library = _by_id(_libraries(request), request.GET['document_library'])
    fields = [
        text_field(request.GET, 'name', 'Nazwa dokumentu', 'file-text', 'title'),
        text_field(request.GET, 'filename', 'Nazwa pliku', 'file', 'filename'),
        text_field(request.GET, 'description', 'Opis', 'align-left', 'description'),
        choice_field(request.GET, 'tag', 'Tagi', 'tag', (
            {'value': str(tag.pk), 'label': tag.name} for tag in tags
        ), searchable=True),
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
        fields.insert(3, choice_field(request.GET, 'document_library', 'Biblioteka', 'library-big', (
            {'value': str(item.pk), 'label': item.name} for item in _libraries(request)
        ), searchable=True))
    sort_fields = tuple(
        {**field, 'label': 'Usunięto', 'lookup': 'deleted_at'}
        if current_view == 'trash' and field['value'] == 'updated' else field
        for field in DOCUMENT_SORT_FIELDS
    )
    query_state = query_context(request.GET, fields, sort_fields, 'updated_desc')
    values = query_state['document_filter_params']
    # Searching/filtering spans nested folders within the current library, as tag search does.
    searching = bool(query or query_state['has_active_filters'])
    document_only_filter = any(field['active'] and field['param'] not in {'name', 'modified'} for field in fields)
    documents = _documents(request).filter(deleted_at__isnull=current_view != 'trash')
    if current_library:
        documents = documents.filter(library=current_library)
    elif selected_library:
        documents = documents.filter(library=selected_library)
    library_folders = _folders(request).filter(library=current_library) if current_library else Folder.objects.none()
    folders = library_folders if current_view == 'all' and not document_only_filter else Folder.objects.none()
    if not searching:
        folders = folders.filter(parent=folder)
    if current_view == 'starred':
        documents = documents.filter(is_starred=True)
    if query:
        documents = documents.filter(Q(title__icontains=query) | Q(filename__icontains=query) | Q(description__icontains=query) | Q(tags__name__icontains=query)).distinct()
        folders = folders.filter(name__icontains=query)
    elif current_library and current_view == 'all' and not searching:
        documents = documents.filter(folder=folder)
    if selected_tag:
        documents = documents.filter(tags=selected_tag)
    documents = apply_text_filters(documents, fields)
    folders = apply_text_filters(folders, [{**field, 'lookup': 'name'} for field in fields if field['param'] == 'name'])
    documents = apply_date_filter(documents, 'deleted_at' if current_view == 'trash' else 'updated_at', values['modified'])
    folders = apply_date_filter(folders, 'created_at', values['modified'])
    if values['file_type']:
        documents = documents.filter(filename__iendswith=values['file_type'])
    if values['starred']:
        documents = documents.filter(is_starred=values['starred'] == 'yes')
    if values['size'] == 'small':
        documents = documents.filter(file_size__lt=1024 * 1024)
    elif values['size'] == 'medium':
        documents = documents.filter(file_size__gte=1024 * 1024, file_size__lte=5 * 1024 * 1024)
    elif values['size'] == 'large':
        documents = documents.filter(file_size__gt=5 * 1024 * 1024)
    documents = order_results(documents.select_related('folder', 'owner', 'library').prefetch_related('tags'), query_state)
    folder_sort = query_state['sort_field'] if query_state['sort_field'] in {'name', 'updated', 'created'} else 'name'
    folder_sort_fields = (
        {'value': 'name', 'lookup': 'name', 'text': True},
        {'value': 'updated', 'lookup': 'created_at'}, {'value': 'created', 'lookup': 'created_at'},
    )
    folders = order_results(folders, {**query_state, 'sort_fields': folder_sort_fields, 'sort_field': folder_sort})
    folder_count = folders.count()
    page, window = _pagination(request, folder_count + documents.count())
    start, end = (page.start_index() - 1 if page.paginator.count else 0), page.end_index()
    rows = [
        {'kind': 'folder', 'item': item, 'url': _url(request, library=current_library.pk, folder=item.pk)}
        for item in folders[start:end]
    ] if start < folder_count else []
    if end > folder_count:
        rows += [
            {'kind': 'document', 'item': item, 'url': _url(request, f'{item.pk}/')}
            for item in documents[max(0, start - folder_count):end - folder_count]
        ]
    library_id = current_library.pk if current_library else None
    view_label = next(option['label'] for option in DOCUMENT_VIEW_OPTIONS if option['value'] == current_view)
    context = _context(request, current_library, folder)
    context.update(_sidebar(request, active_view=current_view if not current_library else None))
    context.update(query_state)
    context.update({
        'clear_url': _url(request, library=library_id, view=current_view, folder=folder.pk if folder else None),
        'view_url': _url(request, library=library_id, view=current_view, folder=folder.pk if folder else None),
        'tag_filter_query': urlencode({key: value for key, value in {
            **values, 'q': query, 'sort': query_state['sort_param'], 'page_size': window['page_size'],
        }.items() if key != 'tag' and value not in ('', None)}),
        'rows': rows, 'page': page, 'query': query, 'document_window': window, 'document_form': form_context,
        'library_view': current_view, 'tags': tags, 'selected_tag': selected_tag,
        'view_label': view_label,
        'view_title': (folder.name if folder and not searching and current_view == 'all' else current_library.name) if current_library else view_label,
    })
    return render(request, 'documents/library.html', context)


def _render_form(request, context):
    context['form_action'] = request.get_full_path()
    if request.headers.get('X-Document-Modal') == 'true':
        return render(request, 'documents/form.html', {'modal': context})
    # Direct links and ordinary form submissions use the same dialog over its list.
    background_request = copy(request)
    background_request.GET = QueryDict(urlsplit(context['folder_url']).query)
    return _library_page(background_request, context)


def _form_success(request, url):
    if request.headers.get('X-Document-Modal') == 'true':
        return JsonResponse({'redirect_url': url})
    return redirect(url)


def _save_library(request, instance=None):
    form = LibraryForm(request.POST if request.method == 'POST' else None, instance=instance, owner=request.user, workplace=request.workplace)
    if request.method == 'POST' and form.is_valid():
        item = form.save(commit=False)
        item.owner, item.workplace = request.user, request.workplace
        try:
            with transaction.atomic():
                item.save()
        except IntegrityError:
            form.add_error('name', 'Biblioteka o tej nazwie już istnieje w tym Workspace.')
        else:
            messages.success(request, 'Zapisano bibliotekę.' if instance else 'Utworzono bibliotekę dokumentów.')
            return _form_success(request, _url(request, library=item.pk))
    context = _context(request, instance)
    context.update({'form': form, 'form_title': 'Ustawienia biblioteki' if instance else 'Nowa biblioteka dokumentów', 'submit_label': 'Zapisz bibliotekę' if instance else 'Utwórz bibliotekę'})
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
@require_POST
def library_delete(request, pk):
    item = get_object_or_404(_libraries(request), pk=pk)
    try:
        item.delete()
    except RestrictedError:
        messages.error(request, 'Można usunąć tylko pustą bibliotekę. Zawiera ona foldery lub pliki, również w koszu.')
    else:
        messages.success(request, 'Usunięto pustą bibliotekę.')
    return redirect(_url(request))


@login_required
@require_http_methods(['GET', 'POST'])
def upload(request):
    current_library, folder = _location(request)
    form = UploadForm(request.POST if request.method == 'POST' else None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        saved_files = []
        try:
            with transaction.atomic():
                for file in form.cleaned_data['files']:
                    document = Document(owner=request.user, workplace=request.workplace, library=current_library, folder=folder,
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
    form = FolderForm(request.POST if request.method == 'POST' else None, instance=folder, owner=request.user, workplace=request.workplace, library=current_library, parent=parent)
    if request.method == 'POST' and form.is_valid():
        item = form.save(commit=False)
        item.owner, item.workplace, item.parent, item.library = request.user, request.workplace, parent, current_library
        try:
            with transaction.atomic():
                item.save()
        except IntegrityError:
            form.add_error('name', 'Folder o tej nazwie już istnieje w tym miejscu.')
        else:
            messages.success(request, 'Zapisano folder.' if folder else 'Utworzono folder.')
            return _form_success(request, _url(request, library=current_library.pk, folder=parent.pk if parent else None))
    context = _context(request, current_library, parent)
    context.update({'form': form, 'form_title': 'Zmień nazwę folderu' if folder else 'Nowy folder', 'submit_label': 'Zapisz folder'})
    return _render_form(request, context)


@login_required
@require_http_methods(['GET', 'POST'])
def folder_create(request):
    return _save_folder(request)


@login_required
@require_http_methods(['GET', 'POST'])
def folder_edit(request, pk):
    return _save_folder(request, get_object_or_404(_folders(request).select_related('library'), pk=pk))


@login_required
@require_POST
def folder_delete(request, pk):
    folder = get_object_or_404(_folders(request), pk=pk)
    parent_id, library_id = folder.parent_id, folder.library_id
    try:
        folder.delete()
    except RestrictedError:
        messages.error(request, 'Folder zawiera podfoldery lub dokumenty (również w koszu). Najpierw je przenieś.')
    else:
        messages.success(request, 'Usunięto pusty folder.')
    return redirect(_url(request, library=library_id, folder=parent_id))


@login_required
@require_http_methods(['GET', 'POST'])
def detail(request, pk):
    document = get_object_or_404(_documents(request).select_related('folder', 'library'), pk=pk, deleted_at__isnull=True)
    form = DocumentForm(request.POST if request.method == 'POST' else None, instance=document, owner=request.user, workplace=request.workplace)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Zapisano dokument.')
        return _form_success(request, _url(request, library=document.library_id, folder=form.instance.folder_id))
    context = _context(request, document.library, document.folder)
    context.update({'form': form, 'document': document, 'form_title': document.title, 'submit_label': 'Zapisz zmiany'})
    return _render_form(request, context)


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
    params = {key: request.POST.get(key, '') for key in dict.fromkeys(('view', 'folder', 'q', 'tag', 'sort', 'page', 'page_size', *FILTER_PARAMETERS))}
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
    document = get_object_or_404(_documents(request), pk=pk, deleted_at__isnull=True)
    document.deleted_at = timezone.now()
    document.save(update_fields=['deleted_at'])
    messages.success(request, 'Dokument przeniesiono do kosza. Możesz go przywrócić.')
    return _return_to_library(request, document)


@login_required
@require_POST
def restore(request, pk):
    document = get_object_or_404(_documents(request), pk=pk, deleted_at__isnull=False)
    document.deleted_at = None
    document.save(update_fields=['deleted_at'])
    messages.success(request, 'Przywrócono dokument do jego folderu.')
    return _return_to_library(request, document)
