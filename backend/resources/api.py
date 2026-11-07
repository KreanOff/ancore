import csv
import io
import json
from datetime import timedelta

from django import forms
from core.list_window import window_page, window_url
from django.db import transaction
from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone

from accounts.avatar import account_avatar
from core.api import api_error, api_view, json_object
from workplaces.services import workspace_owner
from .forms import ResourceForm, ResourceOperationForm
from .models import Resource
from .services import directory_context, filtered_resources, record_activity, resource_base_url, resource_scope, resource_snapshot, save_resource_form


def resource_payload(resource):
    today = timezone.localdate()
    active = resource.status != Resource.Status.RETIRED
    return {
        'id': resource.pk,
        **{field: getattr(resource, field) for field in (
            'name', 'kind', 'inventory_number', 'serial_number', 'status', 'location', 'notes',
        )},
        'assigned_to': resource.assigned_to_id or '',
        'assignee_name': (resource.assigned_to.get_full_name() or resource.assigned_to.email) if resource.assigned_to else 'Nieprzypisany',
        'purchased_on': resource.purchased_on.isoformat() if resource.purchased_on else '',
        'expires_on': resource.expires_on.isoformat() if resource.expires_on else '',
        'return_due_on': resource.return_due_on.isoformat() if resource.return_due_on else '',
        'updated_at': resource.updated_at.isoformat(),
        'created_at': resource.created_at.isoformat(),
        'kind_label': resource.get_kind_display(), 'status_label': resource.get_status_display(),
        'icon': resource.icon,
        'overdue': bool(active and resource.expires_on and resource.expires_on < today),
        'expiring_soon': bool(active and resource.expires_on and today <= resource.expires_on <= today + timedelta(days=30)),
        'return_overdue': bool(resource.return_due_on and resource.return_due_on < today),
    }


def editor_payload(form):
    fields = []
    for name, field in form.fields.items():
        value = form[name].value()
        info = {
            'name': name, 'label': str(field.label), 'required': field.required,
            'help_text': str(field.help_text), 'value': '' if value is None else str(value),
            'type': 'text', 'max_length': getattr(field, 'max_length', None),
            'placeholder': field.widget.attrs.get('placeholder', ''),
        }
        if isinstance(field, forms.ModelChoiceField):
            info['type'] = 'select'
            info['choices'] = [
                {'value': '', 'label': str(field.empty_label)},
                *[{'value': str(person.pk), 'label': field.label_from_instance(person), 'avatar': account_avatar(person)} for person in field.queryset],
            ]
        elif isinstance(field, forms.ChoiceField):
            info['type'] = 'select'
            info['choices'] = [{'value': str(value), 'label': str(label)} for value, label in field.choices]
        elif isinstance(field.widget, forms.Textarea):
            info['type'] = 'textarea'
        elif isinstance(field, forms.DateField):
            info['type'] = 'date'
        fields.append(info)
    return {'id': form.instance.pk, 'fields': fields, 'revision': form.instance.updated_at.isoformat() if form.instance.pk else ''}


def directory_payload(request, context=None):
    from workplaces.policy import read_only
    context = context if context is not None else directory_context(request)
    return {
        'read_only': read_only(request),
        'results': [resource_payload(item) for item in context['resources']],
        'list_url': context['list_url'], 'base_url': context['resources_url'],
        'api_url': resource_base_url(request) + 'api/v1/',
        'query': context['query'], 'filters': context['filters'], 'has_filters': context['has_filters'],
        'sort': context['sort'], 'sort_label': context['sort_label'], 'sort_options': context['sort_options'],
        'pagination': context['resource_window'],
        'summary': context['resource_summary'], 'export_url': context['export_url'],
    }


def _save(request, resource):
    try:
        data = json_object(request)
    except ValueError as error:
        return api_error(str(error), 400)
    form = ResourceForm(data, instance=resource, workplace=request.workplace)
    if not save_resource_form(form, request.user, revision=data.get('revision')):
        return api_error('Popraw zaznaczone pola.', 400, errors=form.errors.get_json_data(), editor=editor_payload(form))
    return None


@api_view(['GET', 'POST'])
def collection(request):
    if request.method == 'POST':
        resource = Resource(owner=workspace_owner(request), workplace=request.workplace, created_by=request.user)
        error = _save(request, resource)
        if error is not None:
            return error
        return JsonResponse({'resource': resource_payload(resource)}, status=201)
    return JsonResponse(directory_payload(request))


@api_view(['GET'])
def new(request):
    # Validate membership even when returning an empty form.
    owner = workspace_owner(request)
    form = ResourceForm(instance=Resource(owner=owner, workplace=request.workplace), workplace=request.workplace)
    return JsonResponse(editor_payload(form))


@api_view(['GET', 'PUT'])
def detail(request, pk):
    resource = get_object_or_404(resource_scope(request).select_related('assigned_to'), pk=pk)
    if request.method == 'PUT':
        error = _save(request, resource)
        if error is not None:
            return error
    if request.method == 'GET':
        return JsonResponse(editor_payload(ResourceForm(instance=resource, workplace=request.workplace)))
    return JsonResponse({'resource': resource_payload(resource)})


@api_view(['POST'])
def delete(request, pk):
    get_object_or_404(resource_scope(request), pk=pk).delete()
    return JsonResponse({'deleted': True})


def overview_payload(request, resource):
    page = window_page(resource.activities.all(), request, limit_parameter='history_limit', page_parameter='history_page')
    return {
        'resource': resource_payload(resource),
        'history': [{'id': entry.pk, 'action': entry.action, 'label': entry.get_action_display(),
                     'actor': entry.actor_name, 'created_at': entry.created_at.isoformat(),
                     'changes': entry.changes, 'note': entry.note} for entry in page],
        'history_page': page.number, 'history_pages': page.paginator.num_pages,
        'history_total': page.paginator.count, 'history_end': page.end_index(),
        'history_next': window_url(request, page),
    }


@api_view(['GET'])
def overview(request, pk):
    resource = get_object_or_404(resource_scope(request).select_related('assigned_to'), pk=pk)
    return JsonResponse(overview_payload(request, resource))


@api_view(['POST'])
def operate(request):
    try:
        data = json_object(request)
        raw_ids = data.get('ids', '')
        if not isinstance(raw_ids, str):
            raise ValueError
        ids = raw_ids.split(',')
        if not 1 <= len(ids) <= 100 or any(not value.isascii() or not value.isdigit() or len(value) > 18 for value in ids):
            raise ValueError
        ids = {int(value) for value in ids}
        revisions = json.loads(data.get('revisions', '{}'))
        if not isinstance(revisions, dict) or any(not isinstance(revisions.get(str(pk)), str) for pk in ids):
            raise ValueError
    except (ValueError, TypeError):
        return api_error('Wybierz od 1 do 100 zasobów i odśwież ich dane.', 400)
    form = ResourceOperationForm(data, workplace=request.workplace)
    if not form.is_valid():
        return api_error('Popraw zaznaczone pola.', 400, errors=form.errors.get_json_data())
    values = form.cleaned_data
    action = values['action']
    with transaction.atomic():
        # Stable ordering also prevents opposite bulk selections from deadlocking.
        resources = list(resource_scope(request).select_for_update().filter(pk__in=ids).order_by('pk'))
        if len(resources) != len(ids):
            return api_error('Co najmniej jeden zasób jest niedostępny. Odśwież listę.', 404)
        for resource in resources:
            if revisions[str(resource.pk)] != resource.updated_at.isoformat():
                return api_error('Dane zasobów uległy zmianie. Zamknij okno i odśwież listę przed ponowieniem operacji.', 409)
            if action == 'handover' and resource.status not in {Resource.Status.AVAILABLE, Resource.Status.IN_USE}:
                return api_error('Można przekazać wyłącznie zasoby dostępne lub w użyciu. Zmień zaznaczenie lub status.', 400)
            if action == 'return' and resource.status != Resource.Status.IN_USE:
                return api_error('Zwrot dotyczy wyłącznie zasobów w użyciu. Zmień zaznaczenie.', 400)
        for resource in resources:
            before = resource_snapshot(resource)
            if action == 'handover':
                resource.assigned_to = values['assigned_to']
                resource.status = Resource.Status.IN_USE
                resource.return_due_on = values['return_due_on']
            elif action == 'return':
                resource.assigned_to = None
                resource.status = Resource.Status.AVAILABLE
                resource.return_due_on = None
            elif action == 'status':
                resource.status = values['status']
                if resource.status != Resource.Status.IN_USE:
                    resource.return_due_on = None
            elif action == 'location':
                resource.location = values['location']
            resource.updated_by = request.user
            resource.save()
            record_activity(resource, request.user, before, action, values['note'])
    return JsonResponse({'updated': len(resources)})


def csv_cell(value):
    value = str(value or '')
    # Spreadsheet programs may evaluate formulas even in quoted CSV cells.
    return "'" + value if value.lstrip().startswith(('=', '+', '-', '@')) or value.startswith(('\t', '\r', '\n')) else value


@api_view(['GET'])
def export(request):
    queryset = filtered_resources(request)
    def rows():
        buffer = io.StringIO()
        writer = csv.writer(buffer, delimiter=';')
        yield '\ufeff'
        headings = ['Nazwa', 'Typ', 'Numer ewidencyjny', 'Numer seryjny', 'Status', 'Osoba odpowiedzialna', 'Lokalizacja', 'Data zakupu', 'Ważność / gwarancja', 'Planowany zwrot', 'Notatki']
        writer.writerow(headings)
        yield buffer.getvalue()
        for resource in queryset.iterator(chunk_size=500):
            buffer.seek(0)
            buffer.truncate()
            item = resource_payload(resource)
            writer.writerow([csv_cell(item[key]) for key in ['name', 'kind_label', 'inventory_number', 'serial_number', 'status_label', 'assignee_name', 'location', 'purchased_on', 'expires_on', 'return_due_on', 'notes']])
            yield buffer.getvalue()
    response = StreamingHttpResponse(rows(), content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="zasoby.csv"'
    response['X-Content-Type-Options'] = 'nosniff'
    return response
