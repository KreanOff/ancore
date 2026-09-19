"""Dokumenty: a separate workspace catalog using the shared document infrastructure."""
from copy import copy
from io import BytesIO
import json
import uuid
from urllib.parse import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import SuspiciousFileOperation, ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.db.models.deletion import RestrictedError
from django.http import FileResponse, Http404, JsonResponse, QueryDict
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.text import get_valid_filename
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from core.upload_validation import attachment_download_response
from workplaces.services import scoped_workplace_app_path
from .editor_forms import OfficeDocumentForm, OfficeFolderForm, OfficeUploadForm
from .models import WorkspaceDocument as Document, WorkspaceDocumentFolder as Folder
from .previews import build_preview, validate_inline
from .rich_text import docx_bytes, text_to_content
from .views import _form_success


def _url(request, suffix='', **params):
    base = scoped_workplace_app_path(request.workplace, 'office', suffix)
    query = urlencode({key: value for key, value in params.items() if value not in ('', None)})
    return f'{base}?{query}' if query else base


def _documents(request):
    return Document.objects.filter(owner=request.user, workplace=request.workplace)


def _folders(request):
    return Folder.objects.filter(owner=request.user, workplace=request.workplace)


def _folder(request, value):
    if not value:
        return None
    try:
        return get_object_or_404(_folders(request), pk=int(value))
    except (ValueError, TypeError, OverflowError):
        raise Http404


def _item(request, pk, **filters):
    return get_object_or_404(_documents(request).select_related('folder'), pk=pk, deleted_at__isnull=True, **filters)


def _context(request, folder=None):
    breadcrumbs, seen, current = [], set(), folder
    while current and current.pk not in seen:
        seen.add(current.pk)
        breadcrumbs.append({'name': current.name, 'url': _url(request, folder=current.pk)})
        current = _folder(request, current.parent_id)
    folder_id = folder.pk if folder else None
    return {'documents_url': _url(request), 'folder_url': _url(request, folder=folder_id),
            'current_folder': folder, 'breadcrumbs': list(reversed(breadcrumbs)),
            'create_url': _url(request, 'create/', folder=folder_id),
            'upload_url': _url(request, 'upload/', folder=folder_id),
            'folder_create_url': _url(request, 'folders/create/', folder=folder_id)}


@login_required
@require_GET
def index(request):
    return _list(request)


def _list(request, modal=None):
    folder = _folder(request, request.GET.get('folder'))
    view = request.GET.get('view', 'all')
    if view not in {'all', 'recent', 'starred', 'trash'}:
        view = 'all'
    query = request.GET.get('q', '').strip()[:120]
    display_key = f'office_display:{request.user.pk}:{request.workplace.pk}'
    display = request.GET.get('display', request.session.get(display_key, 'list'))
    if display not in {'list', 'grid'}:
        display = 'list'
    request.session[display_key] = display
    sorting = request.GET.get('sort', 'updated')
    order = {'updated': ['-updated_at', 'title', 'pk'], 'name': ['title', 'pk'], 'oldest': ['updated_at', 'pk']}
    if sorting not in order:
        sorting = 'updated'
    items = _documents(request).filter(deleted_at__isnull=view != 'trash')
    folders = _folders(request) if view == 'all' else Folder.objects.none()
    if view == 'starred':
        items = items.filter(is_starred=True)
    if query:
        items = items.filter(Q(title__icontains=query) | Q(filename__icontains=query))
        folders = folders.filter(name__icontains=query)
    elif view == 'all':
        items, folders = items.filter(folder=folder), folders.filter(parent=folder)
    # Searches and special views cover all folders in this Workspace.
    try:
        size = int(request.GET.get('page_size', 25))
    except (TypeError, ValueError):
        size = 25
    if size not in {25, 50, 100}:
        size = 25
    folder_count = folders.count()
    total = folder_count + items.count()
    page = Paginator(range(total), size).get_page(request.GET.get('page'))
    start, end = max(0, page.start_index() - 1), page.end_index()
    rows = [{'kind': 'folder', 'item': item, 'url': _url(request, folder=item.pk)} for item in folders[start:end]] if start < folder_count else []
    if end > folder_count:
        rows += [{'kind': 'document', 'item': item, 'url': _url(request, f'{item.pk}/editor/' if item.has_full_editor else (f'{item.pk}/' if item.kind == Document.Kind.TEXT else f'{item.pk}/preview/'))} for item in items.select_related('folder').order_by(*order[sorting])[max(0, start-folder_count):end-folder_count]]
    params = {'folder': folder.pk if folder else None, 'view': view, 'q': query, 'sort': sorting, 'display': display, 'page_size': size}
    counts = _documents(request).aggregate(all=Count('pk', filter=Q(deleted_at__isnull=True)), starred=Count('pk', filter=Q(deleted_at__isnull=True, is_starred=True)), trash=Count('pk', filter=Q(deleted_at__isnull=False)))
    context = _context(request, folder)
    context.update({
        'rows': rows, 'query': query, 'office_view': view, 'document_display': display, 'sort': sorting,
        'document_form': modal, 'clear_url': _url(request, folder=folder.pk if folder else None, view=view),
        'return_query': urlencode({**{key: value for key, value in params.items() if value is not None}, 'page': page.number}),
        'office_views': [{'value': key, 'label': label, 'icon': icon, 'count': counts.get(key), 'active': view == key and not folder,
                         'url': _url(request, view=key)} for key, label, icon in [
                             ('all', 'Wszystkie dokumenty', 'files'), ('recent', 'Ostatnio zmienione', 'clock-3'),
                             ('starred', 'Oznaczone gwiazdką', 'star'), ('trash', 'Kosz', 'trash-2')]],
        'display_options': [{'label': label, 'icon': icon, 'active': display == key, 'url': _url(request, **{**params, 'display': key})}
                            for key, label, icon in [('list', 'Lista', 'list'), ('grid', 'Kafelki', 'layout-grid')]],
        'document_window': {'page': page.number, 'total_pages': page.paginator.num_pages, 'page_size': size, 'page_size_options': [25, 50, 100],
                            'has_previous': page.has_previous(), 'has_next': page.has_next(),
                            'previous_url': _url(request, **{**params, 'page': page.previous_page_number()}) if page.has_previous() else '',
                            'next_url': _url(request, **{**params, 'page': page.next_page_number()}) if page.has_next() else '',
                            'compact_summary': f'{page.start_index()}–{page.end_index()} z {total}', 'summary': f'{total} elementów'},
    })
    return render(request, 'documents/office/index.html', context)


def _modal(request, context, preview=False):
    context['form_action'] = request.get_full_path()
    if request.headers.get('X-Document-Modal') == 'true':
        return render(request, 'documents/preview.html' if preview else 'documents/form.html', {'modal': context})
    background = copy(request)
    background.GET = request.GET.copy()
    background.GET['folder'] = str(context['current_folder'].pk) if context.get('current_folder') else ''
    return _list(background, context)


@login_required
@require_http_methods(['GET', 'POST'])
def folder_edit(request, pk=None):
    instance = get_object_or_404(_folders(request), pk=pk) if pk else None
    parent = _folder(request, instance.parent_id if instance else request.GET.get('folder'))
    form = OfficeFolderForm(request.POST if request.method == 'POST' else None, instance=instance, owner=request.user, workplace=request.workplace, parent=parent)
    if request.method == 'POST' and form.is_valid():
        item = form.save(commit=False)
        item.owner, item.workplace, item.parent = request.user, request.workplace, parent
        try:
            with transaction.atomic():
                item.save()
        except IntegrityError:
            form.add_error('name', 'Folder o tej nazwie już istnieje w tym miejscu.')
        else:
            messages.success(request, 'Zapisano folder.')
            return _form_success(request, _url(request, folder=parent.pk if parent else None))
    return _modal(request, {**_context(request, parent), 'form': form, 'form_title': 'Zmień nazwę folderu' if instance else 'Nowy folder', 'submit_label': 'Zapisz folder'})


@login_required
@require_POST
def folder_delete(request, pk):
    folder = get_object_or_404(_folders(request), pk=pk)
    parent_id = folder.parent_id
    try:
        folder.delete()
    except RestrictedError:
        messages.error(request, 'Można usunąć tylko pusty folder. Zawiera dokumenty, podfoldery lub dokumenty w koszu.')
    else:
        messages.success(request, 'Usunięto pusty folder.')
    return redirect(_url(request, folder=parent_id))


@login_required
@require_http_methods(['GET', 'POST'])
def upload(request):
    folder = _folder(request, request.GET.get('folder'))
    form = OfficeUploadForm(request.POST if request.method == 'POST' else None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        saved = []
        try:
            with transaction.atomic():
                for file in form.cleaned_data['files']:
                    item = Document(owner=request.user, workplace=request.workplace, folder=folder, kind=Document.Kind.FILE,
                                    title=file.name, filename=file.name, file_size=file.size)
                    item.file.save(file.name, file, save=False)
                    saved.append((item.file.storage, item.file.name))
                    item.save()
        except Exception:
            for storage, name in saved:
                storage.delete(name)
            raise
        messages.success(request, f'Przesłano dokumenty: {len(saved)}.')
        return _form_success(request, _url(request, folder=folder.pk if folder else None))
    return _modal(request, {**_context(request, folder), 'form': form, 'form_title': 'Prześlij dokumenty', 'submit_label': 'Prześlij dokumenty',
                           'upload_form': True, 'office_upload': True, 'max_upload_size': settings.MAX_ATTACHMENT_SIZE})


@login_required
@require_http_methods(['GET', 'POST'])
def edit(request, pk=None):
    instance = _item(request, pk) if pk else Document(owner=request.user, workplace=request.workplace, folder=_folder(request, request.GET.get('folder')))
    is_new = pk is None
    original_folder = instance.folder
    form = OfficeDocumentForm(request.POST if request.method == 'POST' else None, request.FILES or None, instance=instance, owner=request.user, workplace=request.workplace)
    conflict = False
    if request.method == 'POST' and form.is_valid():
        item = form.save(commit=False)
        previous_name = item.file.name
        saved_name = None
        try:
            with transaction.atomic():
                locked = get_object_or_404(_documents(request).select_for_update(), pk=pk, deleted_at__isnull=True) if pk else None
                if locked and locked.revision != form.cleaned_data['revision']:
                    conflict = True
                    form.add_error(None, 'Dokument zmieniono w innym oknie. Twoja treść pozostaje w edytorze. Otwórz aktualny dokument w nowej karcie i porównaj zmiany przed zapisem.')
                else:
                    if locked:
                        item.revision = locked.revision + 1
                        # Star/trash changes are independent of the editing form.
                        item.is_starred = locked.is_starred
                        item.office_key = locked.office_key
                        item.office_save_error = locked.office_save_error
                    replacement = form.cleaned_data.get('replacement')
                    if replacement:
                        item.file.save(replacement.name, replacement, save=False)
                        saved_name = item.file.name
                        item.filename, item.file_size = replacement.name, replacement.size
                        item.office_key, item.office_save_error = uuid.uuid4(), False
                    elif item.kind == Document.Kind.TEXT:
                        item.file_size = len(item.content.encode('utf-8'))
                    item.save()
        except Exception:
            if saved_name:
                item.file.storage.delete(saved_name)
            raise
        if not conflict:
            if saved_name and previous_name and previous_name != saved_name:
                storage = item.file.storage
                transaction.on_commit(lambda: storage.delete(previous_name), robust=True)
            target = _url(request, f'{item.pk}/') if item.kind == Document.Kind.TEXT else _url(request, folder=item.folder_id)
            if request.headers.get('X-Office-Editor') == 'true':
                return JsonResponse({'url': target, 'revision': item.revision, 'saved_at': timezone.localtime(item.updated_at).strftime('%H:%M'), 'title': item.title})
            messages.success(request, 'Utworzono dokument.' if is_new else 'Zapisano dokument.')
            return _form_success(request, target)
    if request.method == 'POST' and request.headers.get('X-Office-Editor') == 'true':
        return JsonResponse({'errors': form.errors.get_json_data()}, status=409 if conflict else 400)
    context = {**_context(request, original_folder), 'form': form, 'document': instance, 'is_new': is_new}
    if instance.kind != Document.Kind.TEXT:
        context.update({'form_title': 'Dane dokumentu', 'submit_label': 'Zapisz zmiany'})
        return _modal(request, context)
    response = render(request, 'documents/office/editor.html', context)
    response['Cache-Control'] = 'private, no-store'
    return response


@login_required
@require_GET
def preview(request, pk):
    item = _item(request, pk)
    if item.kind == Document.Kind.TEXT:
        return redirect(_url(request, f'{item.pk}/'))
    if item.has_full_editor:
        return redirect(_url(request, f'{pk}/editor/'))
    result = build_preview(item)
    context = {**_context(request, item.folder), 'document': item, 'preview': result, 'content_url': _url(request, f'{pk}/content/')}
    from .office_service import LEGACY_FORMATS, configured
    if item.extension in LEGACY_FORMATS and configured():
        context['office_convert_url'] = _url(request, f'{pk}/convert/')
    if item.extension in {'TXT', 'DOCX'} and result['kind'] == 'text' and not result.get('truncated'):
        context['office_import_url'] = _url(request, f'{pk}/import/')
    response = _modal(request, context, preview=True)
    response['Cache-Control'] = 'private, no-store'
    return response


@login_required
@require_POST
def import_text(request, pk):
    source = _item(request, pk, kind=Document.Kind.FILE)
    result = build_preview(source) if source.extension in {'TXT', 'DOCX'} else {}
    if result.get('kind') != 'text' or result.get('truncated'):
        messages.error(request, 'Nie można utworzyć pełnej kopii tekstu z tego pliku. Oryginał pozostaje bez zmian.')
        return redirect(_url(request, f'{pk}/preview/'))
    try:
        content = text_to_content(result['text'])
    except ValidationError as error:
        messages.error(request, error.messages[0])
        return redirect(_url(request, f'{pk}/preview/'))
    item = Document.objects.create(owner=request.user, workplace=request.workplace, folder=source.folder,
                                   title=f'{source.title[:230]} — kopia tekstu', content=content, file_size=len(content.encode('utf-8')))
    messages.success(request, 'Utworzono edytowalną kopię tekstu. Oryginalny plik zachowano.')
    return redirect(_url(request, f'{item.pk}/'))


@login_required
@require_GET
def download(request, pk):
    item = _item(request, pk)
    if item.kind == Document.Kind.BOARD:
        response = FileResponse(BytesIO(item.content.encode()), as_attachment=True, filename=item.title[:230] + '.excalidraw', content_type='application/json')
    elif item.kind == Document.Kind.TEXT:
        try:
            filename = get_valid_filename(item.title[:200])
        except SuspiciousFileOperation:
            filename = 'Dokument'
        response = FileResponse(BytesIO(docx_bytes(item.content)), as_attachment=True, filename=f'{filename}.docx', content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    else:
        try:
            response = attachment_download_response(item)
        except OSError:
            raise Http404('Plik nie jest dostępny.')
    response['Cache-Control'] = 'private, no-store'
    response['X-Content-Type-Options'] = 'nosniff'
    return response


@login_required
@require_GET
@xframe_options_sameorigin
def content(request, pk):
    item = _item(request, pk, kind=Document.Kind.FILE)
    if item.extension != 'PDF' or not item.file:
        raise Http404
    try:
        file = item.file.open('rb')
    except OSError:
        raise Http404
    try:
        validate_inline(file, item.filename)
        response = FileResponse(file, content_type='application/pdf')
    except (OSError, ValueError):
        file.close()
        raise Http404
    response['Cache-Control'] = 'private, no-store'
    response['X-Content-Type-Options'] = 'nosniff'
    response['Content-Security-Policy'] = "sandbox; default-src 'none'; frame-ancestors 'self'"
    return response


@login_required
@require_POST
def action(request, pk, operation):
    with transaction.atomic():
        item = get_object_or_404(_documents(request).select_for_update(), pk=pk, deleted_at__isnull=operation != 'restore')
        if operation == 'star':
            item.is_starred = not item.is_starred
            item.save(update_fields=['is_starred'])
        elif operation in {'trash', 'restore'}:
            item.deleted_at = timezone.now() if operation == 'trash' else None
            item.office_key = uuid.uuid4()
            item.save(update_fields=['deleted_at', 'office_key'])
            messages.success(request, 'Dokument przeniesiono do kosza.' if operation == 'trash' else 'Przywrócono dokument.')
        else:
            raise Http404
    # Rebuild the return path locally; never redirect to a posted external URL.
    params = QueryDict(request.POST.get('return_query', ''))
    allowed = {key: params[key] for key in ('folder', 'view', 'q', 'sort', 'display', 'page', 'page_size') if key in params}
    return redirect(_url(request, **allowed))
