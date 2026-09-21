"""Private document templates."""

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST, require_http_methods

from . import editor_views
from .editor_forms import OfficeTemplateForm, validate_document
from .location_lock import location_write
from .models import WorkspaceDocument


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
