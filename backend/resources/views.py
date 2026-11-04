from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from .forms import ResourceForm
from .models import Resource
from .api import directory_payload, editor_payload, overview_payload
from workplaces.services import workspace_owner
from .services import directory_context, directory_url, resource_base_url, resource_params, resource_scope, save_resource_form


@login_required
@require_GET
def index(request):
    context = directory_context(request)
    context['react_bootstrap'] = directory_payload(request, context)
    if getattr(request, '_react_navigation', False):
        from core.shell import navigation_response
        return navigation_response(request, {'type': 'resources', 'title': 'Zasoby', 'url': request.get_full_path(), 'data': context['react_bootstrap']}, context)
    return render(request, 'resources/react.html', context)


@login_required
@require_http_methods(['GET', 'POST'])
def edit(request, pk=None):
    owner = workspace_owner(request)
    item = get_object_or_404(resource_scope(request), pk=pk) if pk else Resource(owner=owner, workplace=request.workplace, created_by=request.user)
    form = ResourceForm(request.POST if request.method == 'POST' else None, instance=item, workplace=request.workplace)
    ajax = request.headers.get('X-Resource-Modal') == 'true'
    list_url = directory_url(resource_base_url(request), resource_params(request))
    if request.method == 'POST' and save_resource_form(form, request.user, revision=request.POST.get('revision')):
        if ajax:
            return JsonResponse({'saved': True, 'url': list_url})
        messages.success(request, 'Zasób zapisany.')
        return redirect(list_url)
    modal = {'form': form, 'title': 'Edytuj zasób' if pk else 'Dodaj zasób', 'action': request.get_full_path(), 'return_url': list_url}
    if ajax:
        return JsonResponse({'html': render_to_string('resources/form.html', {'modal': modal}, request=request)}, status=400 if request.method == 'POST' else 200)
    context = directory_context(request)
    context['modal'] = modal
    if request.method == 'GET':
        context['react_bootstrap'] = directory_payload(request, context)
        context['react_bootstrap']['editor'] = editor_payload(form)
        if getattr(request, '_react_navigation', False):
            from core.shell import navigation_response
            return navigation_response(request, {'type': 'resources', 'title': 'Zasoby', 'url': request.get_full_path(), 'data': context['react_bootstrap']}, context)
        return render(request, 'resources/react.html', context)
    return render(request, 'resources/index.html', context, status=400)


@login_required
@require_GET
def overview(request, pk):
    resource = get_object_or_404(resource_scope(request).select_related('assigned_to'), pk=pk)
    context = directory_context(request)
    context['resource_detail'] = overview_payload(request, resource)
    context['react_bootstrap'] = {**directory_payload(request, context), 'detail': context['resource_detail']}
    if getattr(request, '_react_navigation', False):
        from core.shell import navigation_response
        return navigation_response(request, {'type': 'resources', 'title': resource.name, 'url': request.get_full_path(), 'data': context['react_bootstrap']}, context)
    return render(request, 'resources/react.html', context)


@login_required
@require_POST
def delete(request, pk):
    item = get_object_or_404(resource_scope(request), pk=pk)
    item.delete()
    url = directory_url(resource_base_url(request), resource_params(request))
    if request.headers.get('X-Resource-Modal') == 'true':
        return JsonResponse({'saved': True, 'url': url})
    messages.success(request, 'Zasób usunięty.')
    return redirect(url)
