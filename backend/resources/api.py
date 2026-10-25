from django import forms
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone

from accounts.avatar import account_avatar
from core.api import api_error, api_view, json_object
from workplaces.services import workspace_owner
from .forms import ResourceForm
from .models import Resource
from .services import directory_context, resource_base_url, resource_scope, save_resource_form


def resource_payload(resource):
    return {
        'id': resource.pk,
        **{field: getattr(resource, field) for field in (
            'name', 'kind', 'inventory_number', 'serial_number', 'status', 'location', 'notes',
        )},
        'assigned_to': resource.assigned_to_id or '',
        'assignee_name': (resource.assigned_to.get_full_name() or resource.assigned_to.email) if resource.assigned_to else 'Nieprzypisany',
        'purchased_on': resource.purchased_on.isoformat() if resource.purchased_on else '',
        'expires_on': resource.expires_on.isoformat() if resource.expires_on else '',
        'kind_label': resource.get_kind_display(), 'status_label': resource.get_status_display(),
        'icon': resource.icon,
        'overdue': bool(resource.expires_on and resource.expires_on < timezone.localdate()),
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
    return {'id': form.instance.pk, 'fields': fields}


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
    }


def _save(request, resource):
    try:
        data = json_object(request)
    except ValueError as error:
        return api_error(str(error), 400)
    form = ResourceForm(data, instance=resource, workplace=request.workplace)
    if not save_resource_form(form, request.user):
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
