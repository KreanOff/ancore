"""Private templates and file history shared by Documents and Drive."""
import uuid

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from . import office_service as service
from . import editor_views, views
from .editor_forms import OfficeTemplateForm, validate_document
from .location_lock import location_write
from .models import WorkspaceDocument
from .suite_views import _private, _suite_item, _suite_url
from .version_service import archive_current


@login_required
@require_http_methods(['GET', 'POST'])
@location_write
def from_template(request):
    form = OfficeTemplateForm(request.POST if request.method == 'POST' else None,
                              owner=request.user, workplace=request.workplace,
                              initial={'template': request.GET.get('template')})
    if request.method == 'POST' and form.is_valid():
        saved = None
        try:
            with transaction.atomic():
                source = get_object_or_404(form.fields['template'].queryset.select_for_update(), pk=form.cleaned_data['template'].pk)
                with source.file.open('rb') as stream:
                    content = stream.read(settings.MAX_ATTACHMENT_SIZE + 1)
                validate_document(SimpleUploadedFile(source.filename, content))
                title = form.cleaned_data['title']
                extension = source.extension.lower()
                item = WorkspaceDocument(owner=request.user, workplace=request.workplace, kind=WorkspaceDocument.Kind.FILE,
                                         title=title, filename=title if title.lower().endswith('.' + extension) else title + '.' + extension,
                                         file_size=len(content), is_pdf_form=source.is_pdf_form)
                item.file.save(item.filename, ContentFile(content), save=False)
                saved = (item.file.storage, item.file.name)
                item.save()
                item.tags.set(source.tags.filter(user=request.user, workplace=request.workplace))
        except (OSError, ValidationError):
            if saved:
                saved[0].delete(saved[1])
            form.add_error(None, 'Nie można odczytać szablonu. Sprawdź plik źródłowy lub wybierz inny szablon.')
        except Exception:
            if saved:
                saved[0].delete(saved[1])
            raise
        else:
            editor_url = editor_views._url(request, f'{item.pk}/editor/')
            if request.headers.get('X-Document-Modal') == 'true':
                return JsonResponse({'redirect_url': editor_views._url(request), 'editor_url': editor_url})
            return redirect(editor_url)
    return editor_views._modal(request, {**editor_views._context(request), 'form': form, 'office_create': True,
                                        'template_create': True, 'form_title': 'Utwórz z szablonu', 'submit_label': 'Utwórz i otwórz',
                                        'has_templates': form.fields['template'].queryset.exists()})


@login_required
@require_POST
def template_toggle(request, pk):
    with transaction.atomic():
        item = get_object_or_404(editor_views._documents(request).select_for_update(), pk=pk, deleted_at__isnull=True)
        if not item.office_type:
            raise Http404
        item.is_template = not item.is_template
        item.save(update_fields=['is_template'])
    messages.success(request, 'Dodano do szablonów.' if item.is_template else 'Usunięto oznaczenie szablonu. Dokument pozostaje w katalogu.')
    return editor_views._action_redirect(request)


@login_required
@require_GET
def history(request, pk, drive=False):
    item = _suite_item(request, pk, drive)
    if not item.file:
        raise Http404
    context = views._context(request, item.library, item.folder) if drive else editor_views._context(request)
    context.update(document=item, drive_editor=drive, versions=Paginator(item.versions.all(), 25).get_page(request.GET.get('page')))
    response = _private(render(request, 'documents/office/history.html', context))
    # Native POST forms need a same-origin Origin/Referer for Django's CSRF check.
    response['Referrer-Policy'] = 'same-origin'
    return response


@login_required
@require_GET
def version_download(request, pk, version, drive=False):
    item = _suite_item(request, pk, drive)
    snapshot = get_object_or_404(item.versions, pk=version)
    try:
        response = FileResponse(snapshot.file.open('rb'), as_attachment=True, filename=snapshot.filename)
    except OSError:
        raise Http404('Plik tej wersji nie jest dostępny.')
    return _private(response)


@login_required
@require_POST
@location_write
def version_restore(request, pk, version, drive=False):
    saved = None
    history_url = _suite_url(request, f'{pk}/history/', drive)
    try:
        with transaction.atomic():
            scoped = views._documents(request) if drive else editor_views._documents(request)
            item = get_object_or_404(scoped.select_for_update(), pk=pk, deleted_at__isnull=True)
            snapshot = get_object_or_404(item.versions, pk=version)
            if str(item.revision) != request.POST.get('revision'):
                messages.error(request, 'Dokument zmieniono w innym oknie. Sprawdź aktualną historię i ponów przywracanie.')
                return redirect(history_url)
            with snapshot.file.open('rb') as stream:
                content = stream.read(settings.MAX_ATTACHMENT_SIZE + 1)
            upload = SimpleUploadedFile(snapshot.filename, content)
            from core.upload_validation import validate_attachment_upload
            validate_attachment_upload(upload)
            service.validate_ooxml(upload, snapshot.filename.rsplit('.', 1)[-1])
            archive_current(item)
            item.file.save(snapshot.filename, ContentFile(content), save=False)
            saved = (item.file.storage, item.file.name)
            item.filename, item.file_size = snapshot.filename, len(content)
            item.revision += 1
            item.office_key, item.office_save_error = uuid.uuid4(), False
            fields = ['file', 'filename', 'file_size', 'revision', 'office_key', 'office_save_error', 'updated_at']
            if not drive:
                item.is_pdf_form = snapshot.is_pdf_form
                fields.append('is_pdf_form')
                if not item.office_type:
                    item.is_template = False
                    fields.append('is_template')
            item.save(update_fields=fields)
    except (OSError, ValidationError):
        if saved:
            saved[0].delete(saved[1])
        messages.error(request, 'Nie można przywrócić tej wersji. Bieżący plik pozostał bez zmian.')
    except Exception:
        if saved:
            saved[0].delete(saved[1])
        raise
    else:
        messages.success(request, f'Przywrócono wersję {snapshot.revision}. Poprzedni plik zachowano w historii. Otwórz ponownie edytor.')
    return redirect(history_url)
