from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import WorkplaceForm
from .models import create_workplace_for_user
from .services import enable_workspace_url_scope, scoped_workplace_app_path, set_active_workplace, workplaces_for_user


@login_required
def workplaces(request):
    enable_workspace_url_scope(request)
    form = WorkplaceForm()

    if request.method == 'POST':
        form = WorkplaceForm(request.POST, request.FILES)
        if form.is_valid():
            name = form.cleaned_data['name']
            if workplaces_for_user(request.user).filter(name__iexact=name).exists():
                form.add_error('name', 'Masz już miejsce pracy o takiej nazwie.')
            else:
                workplace = create_workplace_for_user(request.user, name)
                set_active_workplace(request, workplace)
                messages.success(request, 'Miejsce pracy utworzone.')
                return redirect(scoped_workplace_app_path(workplace, 'tasks'))
        messages.error(request, 'Nie udało się utworzyć miejsca pracy.')

    user_workplaces = workplaces_for_user(request.user)
    return render(request, 'workplaces/workplaces.html', {
        'workplaces': user_workplaces,
        'form': form,
        'active_workplace': getattr(request, 'workplace', None),
    })


@login_required
@require_POST
def switch_workplace(request, workplace_id):
    workplace = get_object_or_404(workplaces_for_user(request.user), pk=workplace_id)
    set_active_workplace(request, workplace)
    enable_workspace_url_scope(request)
    next_url = scoped_workplace_app_path(workplace, 'tasks')
    messages.success(request, f'Przełączono na {workplace.name}.')
    return redirect(next_url)


@login_required
def workplace_home(request, workplace_slug):
    workplace = get_object_or_404(workplaces_for_user(request.user), slug=workplace_slug)
    set_active_workplace(request, workplace)
    enable_workspace_url_scope(request)
    return redirect(scoped_workplace_app_path(workplace, 'tasks'))


@login_required
@require_POST
def update_workplace(request, workplace_id):
    workplace = get_object_or_404(workplaces_for_user(request.user), pk=workplace_id)
    form = WorkplaceForm(request.POST, request.FILES, instance=workplace)
    if form.is_valid():
        name = form.cleaned_data['name']
        duplicate_exists = (
            workplaces_for_user(request.user)
            .filter(name__iexact=name)
            .exclude(pk=workplace.pk)
            .exists()
        )
        if duplicate_exists:
            messages.error(request, 'Masz już miejsce pracy o takiej nazwie.')
        else:
            form.save()
            messages.success(request, 'Ustawienia miejsca pracy zapisane.')
    else:
        messages.error(request, 'Nie udało się zapisać ustawień miejsca pracy.')
    return redirect('workplaces:workplaces')


@login_required
@require_POST
def delete_workplace(request, workplace_id):
    workplaces = workplaces_for_user(request.user)
    workplace = get_object_or_404(workplaces, pk=workplace_id)
    replacement = workplaces.exclude(pk=workplace.pk).first()
    if replacement is None:
        messages.error(request, 'Nie możesz usunąć ostatniego miejsca pracy.')
        return redirect('workplaces:workplaces')

    was_active = getattr(request, 'workplace', None) and request.workplace.pk == workplace.pk
    workplace.delete()
    if was_active:
        set_active_workplace(request, replacement)
    messages.success(request, 'Miejsce pracy usunięte.')
    return redirect('workplaces:workplaces')
