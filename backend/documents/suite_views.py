"""Full office editors and board, with private persistence."""
import json
import logging
import uuid
from io import BytesIO
from urllib.error import URLError

import jwt
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render as django_render
from core.frontend import render
from django.utils import timezone
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from workplaces.services import workspace_owner
from workplaces.policy import read_only

from core.upload_validation import validate_attachment_upload
from . import office_service as service
from .board import EMPTY_SCENE, BOARD_LIMIT, clean_scene
from .editor_forms import OfficeCreateForm, OfficeRenameForm
from .editor_views import _item, _context, _modal, _url
from .file_cleanup import delete_replaced_file
from .location_lock import location_write
from .models import WorkspaceDocument as Document, OfficeSaveReceipt, Document as DriveDocument, DriveOfficeSaveReceipt
from .rich_text import docx_bytes
from .views import _form_success
from . import views as drive_views

logger = logging.getLogger(__name__)


def _private(response):
    response['Cache-Control'] = 'private, no-store'
    response['X-Content-Type-Options'] = 'nosniff'
    response['Referrer-Policy'] = 'no-referrer'
    return response


def _suite_item(request, pk, drive=False):
    if drive:
        return get_object_or_404(drive_views._documents(request).select_related('library', 'folder'),
                                 pk=pk, deleted_at__isnull=True)
    return _item(request, pk)


def _suite_url(request, suffix, drive=False):
    return drive_views._url(request, suffix) if drive else _url(request, suffix)


def _file_queryset(drive=False):
    return DriveDocument.objects.all() if drive else Document.objects.filter(kind=Document.Kind.FILE)


@login_required
@require_http_methods(['GET', 'POST'])
@location_write
def create(request):
    form = OfficeCreateForm(request.POST if request.method == 'POST' else None,
                            initial={'kind': request.GET.get('type', 'word')})
    if request.method == 'POST' and form.is_valid():
        kind, title = form.cleaned_data['kind'], form.cleaned_data['title']
        item = Document(owner=workspace_owner(request), workplace=request.workplace, title=title)
        if kind == 'board':
            item.kind, item.content = Document.Kind.BOARD, json.dumps(EMPTY_SCENE)
            item.filename = title[:240] + '.excalidraw'
            item.file_size = len(item.content.encode())
            item.save()
        else:
            extension = service.OFFICE_FORMATS['pdf' if kind == 'form' else kind][0]
            item.kind = Document.Kind.FILE
            item.is_pdf_form = kind == 'form'
            item.filename = title if title.lower().endswith('.' + extension) else title[:240] + '.' + extension
            data = service.blank_file(kind)
            item.file_size = data.size
            item.file.save(item.filename, data, save=False)
            try:
                item.save()
            except Exception:
                item.file.storage.delete(item.file.name)
                raise
        editor_url = _url(request, f'{item.pk}/editor/')
        if getattr(request, '_react_api', False):
            return JsonResponse({'redirect': _url(request), 'editor_url': editor_url})
        if item.has_full_editor and request.headers.get('X-Document-Modal') == 'true':
            return JsonResponse({'redirect_url': _url(request),
                                 'editor_url': editor_url})
        return _form_success(request, editor_url)
    return _modal(request, {**_context(request), 'form': form, 'office_create': True,
                           'form_title': 'Nowy dokument', 'submit_label': 'Utwórz i otwórz'})


@login_required
@require_GET
def editor(request, pk, drive=False):
    item = _suite_item(request, pk, drive)
    if not item.office_type and (drive or not item.has_full_editor):
        return redirect(_suite_url(request, f'{pk}/preview/' if drive else f'{pk}/', drive))
    location = drive_views._context(request, item.library, item.folder) if drive else _context(request)
    # This full-screen template has no Shell host; layout.js owns its page loader lifecycle.
    context = {**location, 'document': item, 'drive_editor': drive,
               'office_read_only': read_only(request),
               'disable_react_shell': True,
               'office_configured': service.configured(),
               'api_url': settings.ONLYOFFICE_URL + '/web-apps/apps/api/documents/api.js'}
    if item.office_type and service.configured():
        context['editor_config'] = service.editor_config(item, request.user)
    return _private(render(request, 'documents/office/suite.html', context))


@login_required
@require_GET
@xframe_options_sameorigin
def board_frame(request, pk):
    item = _item(request, pk, kind=Document.Kind.BOARD)
    config = {'scene': json.loads(item.content or json.dumps(EMPTY_SCENE)), 'revision': item.revision,
              'saveUrl': _url(request, f'{pk}/board/save/'), 'name': item.title}
    config['readOnly'] = read_only(request)
    response = django_render(request, 'documents/office/board_frame.html', {'board_config': config})
    # Images are data URLs; application assets/fonts and saves stay on this origin.
    response['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self'; worker-src 'self' blob:; frame-src 'none'; frame-ancestors 'self'; base-uri 'none'; form-action 'none'"
    return _private(response)


@login_required
@require_POST
def rename(request, pk, drive=False):
    model = DriveDocument if drive else Document
    with transaction.atomic():
        item = get_object_or_404(model.objects.select_for_update(), pk=pk,
                                 owner=workspace_owner(request), workplace=request.workplace, deleted_at__isnull=True)
        form = OfficeRenameForm(request.POST)
        if not form.is_valid():
            return _private(JsonResponse({'error': form.errors['title'][0]}, status=400))
        if item.title != form.cleaned_data['title']:
            item.title = form.cleaned_data['title']
            # Renaming must not interfere with content saves or the editor session.
            item.save(update_fields=['title', 'updated_at'])
    return _private(JsonResponse({'title': item.title}))


@login_required
@require_POST
def save_board(request, pk):
    item = _item(request, pk, kind=Document.Kind.BOARD)
    try:
        if len(request.body) > BOARD_LIMIT + 10000:
            raise ValidationError('Tablica może mieć maksymalnie 10 MB.')
        data = json.loads(request.body)
        revision = data['revision']
        scene = clean_scene(json.dumps(data['scene'], ensure_ascii=False))
    except (ValidationError, ValueError, KeyError, TypeError, RecursionError) as error:
        return _private(JsonResponse({'error': error.messages[0] if isinstance(error, ValidationError) else 'Nieprawidłowe dane tablicy.'}, status=400))
    with transaction.atomic():
        item = get_object_or_404(Document.objects.select_for_update(), pk=item.pk, owner=workspace_owner(request), workplace=request.workplace, deleted_at__isnull=True)
        if item.revision != revision:
            return _private(JsonResponse({'error': 'Tablica zmieniła się w innym oknie. Pobierz swoją kopię przed ponownym otwarciem.'}, status=409))
        item.content, item.file_size = scene, len(scene.encode())
        item.revision += 1
        item.save(update_fields=['content', 'file_size', 'revision', 'updated_at'])
    return _private(JsonResponse({'revision': item.revision, 'saved_at': timezone.localtime(item.updated_at).strftime('%H:%M:%S')}))


@login_required
@require_POST
def save_office(request, pk, drive=False):
    item = _suite_item(request, pk, drive)
    if not item.office_type or not service.configured():
        return JsonResponse({'error': 'Edytor jest niedostępny.'}, status=503)
    if request.headers.get('X-Office-Key') != service.document_key(item):
        return JsonResponse({'error': 'Plik został podmieniony lub sesja zakończona. Pobierz swoje zmiany z menu Plik edytora i otwórz aktualną wersję.'}, status=409)
    try:
        result = service.force_save(item)
    except (URLError, OSError, ValueError):
        return JsonResponse({'error': 'Nie udało się połączyć z edytorem. Spróbuj ponownie.'}, status=503)
    if result not in (0, 4):
        return JsonResponse({'error': 'Zapis jeszcze nie jest dostępny. Poczekaj na uruchomienie edytora.'}, status=409)
    return _private(JsonResponse({'pending': result == 0, 'revision': item.revision}))


@login_required
@require_GET
def state(request, pk, drive=False):
    item = _suite_item(request, pk, drive)
    return _private(JsonResponse({'revision': item.revision, 'key': service.document_key(item), 'save_error': item.office_save_error,
                                  'saved_at': timezone.localtime(item.updated_at).strftime('%H:%M:%S')}))


def _service_item(request, pk, purpose, drive=False):
    if not service.configured():
        raise Http404
    item = get_object_or_404(_file_queryset(drive), pk=pk, deleted_at__isnull=True)
    if not service.check_capability(item, request.GET.get('token', ''), purpose):
        raise Http404
    return item


@require_GET
def source(request, pk, drive=False):
    item = _service_item(request, pk, 'source', drive)
    try:
        response = FileResponse(item.file.open('rb'), as_attachment=True, filename=item.filename)
    except OSError:
        raise Http404
    return _private(response)


@csrf_exempt
@require_POST
def callback(request, pk, drive=False):
    """Only a server-signed payload can authorize a save; ignore untrusted body fields."""
    if not service.configured():
        return JsonResponse({'error': 1}, status=503)
    token = request.headers.get('Authorization', '').removeprefix('Bearer ')
    try:
        if len(token) > 128000:
            raise ValueError
        payload = service.verify(token)['payload']
        if not isinstance(payload, dict) or type(payload.get('status')) is not int:
            raise ValueError
        key = payload['key']
        if not isinstance(key, str) or len(key) != 64:
            raise ValueError
    except (jwt.PyJWTError, KeyError, TypeError, ValueError):
        return JsonResponse({'error': 1}, status=403)
    digest = service.receipt_digest(payload)
    receipts = DriveOfficeSaveReceipt if drive else OfficeSaveReceipt
    saved_name = None
    try:
        with transaction.atomic():
            item = get_object_or_404(_file_queryset(drive).select_for_update(), pk=pk, deleted_at__isnull=True)
            if receipts.objects.filter(document=item, digest=digest).exists():
                return JsonResponse({'error': 0})
            if key != service.document_key(item) or not service.check_capability(item, request.GET.get('token', ''), 'callback'):
                return JsonResponse({'error': 1}, status=409)
            status = payload['status']
            if status in (3, 7):
                item.office_save_error = True
                item.save(update_fields=['office_save_error'])
                return JsonResponse({'error': 0})
            if status in (1, 4):
                return JsonResponse({'error': 0})
            if status not in (2, 6) or not item.office_type:
                return JsonResponse({'error': 1}, status=400)
            if payload.get('filetype', item.extension.lower()) != item.extension.lower():
                raise ValueError('Unexpected office format')
            content = service.download_result(payload['url'])
            upload = SimpleUploadedFile(item.filename, content)
            validate_attachment_upload(upload)
            service.validate_ooxml(upload, item.extension)
            old_name = item.file.name
            item.file.save(item.filename, ContentFile(content), save=False)
            saved_name = item.file.name
            item.file_size, item.revision, item.office_save_error = len(content), item.revision + 1, False
            if status == 2:
                item.office_key = uuid.uuid4()
            item.save(update_fields=['file', 'file_size', 'revision', 'office_key', 'office_save_error', 'updated_at'])
            receipts.objects.create(document=item, digest=digest)
            delete_replaced_file(item, old_name)
    except (URLError, OSError, ValueError, KeyError, ValidationError):
        if saved_name:
            item.file.storage.delete(saved_name)
        _file_queryset(drive).filter(pk=pk, office_key=item.office_key).update(office_save_error=True)
        # Never log callback URLs, bearer tokens or private document content.
        logger.warning('ONLYOFFICE save failed for document %s', pk)
        return JsonResponse({'error': 1}, status=502)
    except Exception:
        if saved_name:
            item.file.storage.delete(saved_name)
        raise
    return JsonResponse({'error': 0})


@login_required
@require_POST
def upgrade_text(request, pk):
    source = _item(request, pk, kind=Document.Kind.TEXT)
    item = Document(owner=workspace_owner(request), workplace=request.workplace,
                    title=source.title[:235] + ' — DOCX', kind=Document.Kind.FILE,
                    filename=source.title[:230] + '.docx')
    content = docx_bytes(source.content)
    item.file_size = len(content)
    item.file.save(item.filename, ContentFile(content), save=False)
    try:
        item.save()
    except Exception:
        item.file.storage.delete(item.file.name)
        raise
    messages.success(request, 'Utworzono kopię DOCX z treścią i formatowaniem dokumentu.')
    return redirect(_url(request, f'{item.pk}/editor/'))


@login_required
@require_POST
@location_write
def convert(request, pk, drive=False):
    source = _suite_item(request, pk, drive)
    if source.extension not in service.LEGACY_FORMATS or not service.configured():
        raise Http404
    try:
        extension, content = service.convert_file(source)
        service.validate_ooxml(BytesIO(content), extension)
    except (URLError, OSError, ValueError, KeyError, ValidationError):
        messages.error(request, 'Nie udało się przygotować kopii w edytorze. Sprawdź połączenie i spróbuj ponownie.')
        return redirect(_suite_url(request, f'{pk}/preview/', drive))
    model = DriveDocument if drive else Document
    extra = {'library': source.library, 'folder': source.folder, 'description': source.description} if drive else {'kind': Document.Kind.FILE}
    item = model(owner=workspace_owner(request), workplace=request.workplace,
                 title=source.title[:230] + ' — kopia', filename=source.title[:220] + '.' + extension,
                 file_size=len(content), **extra)
    item.file.save(item.filename, ContentFile(content), save=False)
    try:
        with transaction.atomic():
            item.save()
    except Exception:
        item.file.storage.delete(item.file.name)
        raise
    messages.success(request, 'Utworzono kopię do edycji. Oryginalny plik zachowano.')
    return redirect(_suite_url(request, f'{item.pk}/editor/', drive))
