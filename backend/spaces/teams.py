import mimetypes

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from core.frontend import render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from workplaces.models import Workplace
from workplaces.services import workplace_people, workplace_role, workspace_owner
from .forms import MemberForm, TeamDeleteForm, TeamForm
from .models import Team, TeamMembership
from .services import app_url, manage_team, teams_for, visible_spaces
from .team_queries import administrators, detail_context, directory_context
from .views import base_context, decorate_items, dialog_response


@login_required
@require_GET
def index(request):
    return render(request, 'spaces/teams.html', {**base_context(request), **directory_context(request)})


@login_required
@require_GET
def detail(request, pk):
    team = get_object_or_404(teams_for(request), pk=pk)
    context = detail_context(request, team)
    context['items'] = decorate_items(request, context['items'])
    return render(request, 'spaces/team.html', {**base_context(request), **context})


@login_required
@require_http_methods(['GET', 'POST'])
def edit(request, pk=None):
    team = get_object_or_404(teams_for(request), pk=pk) if pk else None
    if workplace_role(request.user, request.workplace) not in {'owner', 'admin', 'member'}:
        raise PermissionDenied
    if team and not manage_team(request, team):
        raise PermissionDenied
    form = TeamForm(request.POST if request.method == 'POST' else None, request.FILES if request.method == 'POST' else None, request=request, team=team)
    url = app_url(request, f'{pk}/' if pk else '', 'teams')
    if request.method == 'POST' and form.is_valid():
        data = form.cleaned_data
        saved_photo = None
        try:
            with transaction.atomic():
                Workplace.objects.select_for_update().get(pk=request.workplace.pk)
                if workplace_role(request.user, request.workplace) not in {'owner', 'admin', 'member'}:
                    raise PermissionDenied
                if pk:
                    team = get_object_or_404(teams_for(request).select_for_update(), pk=pk)
                    if not manage_team(request, team):
                        raise PermissionDenied
                if Team.objects.filter(workplace=request.workplace, name__iexact=data['name']).exclude(pk=pk).exists():
                    form.add_error('name', 'Zespół o tej nazwie już istnieje.')
                    return dialog_response(request, form, 'Edytuj zespół' if pk else 'Utwórz zespół', url)
                visible = visible_spaces(request)
                selected_ids = {space.pk for space in data['spaces']}
                if selected_ids - set(visible.filter(pk__in=selected_ids).values_list('pk', flat=True)):
                    form.add_error('spaces', 'Dostęp do wybranej przestrzeni zmienił się. Odśwież formularz.')
                    return dialog_response(request, form, 'Edytuj zespół' if pk else 'Utwórz zespół', url)
                if team is None:
                    team = Team(owner=workspace_owner(request), workplace=request.workplace, created_by=request.user)
                old_photo = team.photo.name
                team.name, team.description = data['name'], data['description']
                if data.get('photo'):
                    team.photo.save(data['photo'].name, data['photo'], save=False)
                    saved_photo = (team.photo.storage, team.photo.name)
                if data.get('remove_photo'):
                    team.photo = ''
                team.save()
                if old_photo and (saved_photo or data.get('remove_photo')):
                    transaction.on_commit(lambda storage=team.photo.storage, name=old_photo: storage.delete(name), robust=True)
                if not pk:
                    TeamMembership.objects.create(team=team, user=request.user, role='admin')
                # Hidden spaces cannot be removed or discovered by editing a team.
                team.spaces.remove(*team.spaces.filter(pk__in=visible).exclude(pk__in=data['spaces']))
                team.spaces.add(*data['spaces'])
        except Exception:
            if saved_photo:
                saved_photo[0].delete(saved_photo[1])
            raise
        return dialog_response(request, form, '', app_url(request, f'{team.pk}/', 'teams'), saved=True)
    return dialog_response(request, form, 'Edytuj zespół' if pk else 'Utwórz zespół', url)


@login_required
@require_http_methods(['GET', 'POST'])
def members(request, pk, member_pk=None):
    team = get_object_or_404(teams_for(request), pk=pk)
    if not manage_team(request, team):
        raise PermissionDenied
    member = get_object_or_404(team.memberships, pk=member_pk, user__in=workplace_people(request.workplace)) if member_pk else None
    form = MemberForm(request.POST if request.method == 'POST' else None, request=request, team=True,
                      initial={'person': member.user_id, 'role': member.role} if member else {'role': 'member'})
    form.compact = True
    if member:
        form.fields['person'].disabled = True
    else:
        form.fields['person'].queryset = form.fields['person'].queryset.exclude(teammembership__team=team)
    url = app_url(request, f'{pk}/?view=members', 'teams')
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            Workplace.objects.select_for_update().get(pk=request.workplace.pk)
            team = get_object_or_404(teams_for(request).select_for_update(), pk=pk)
            if not manage_team(request, team):
                raise PermissionDenied
            person, role = form.cleaned_data['person'], form.cleaned_data['role']
            old = get_object_or_404(team.memberships, pk=member_pk) if member_pk else None
            if old and old.role == 'admin' and role != 'admin' and administrators(request, team).filter(pk=old.pk).exists() and administrators(request, team).count() == 1:
                form.add_error('role', 'Zespół musi mieć co najmniej jednego aktywnego administratora.')
            elif not workplace_people(request.workplace).filter(pk=person.pk).exists():
                form.add_error('person', 'Ta osoba nie należy już do Workspace.')
            elif role == 'admin' and workplace_role(person, request.workplace) == 'guest':
                form.add_error('role', 'Gość Workspace nie może być administratorem zespołu.')
            elif not member_pk and team.memberships.filter(user=person).exists():
                form.add_error('person', 'Ta osoba już należy do zespołu.')
            else:
                TeamMembership.objects.update_or_create(team=team, user=person, defaults={'role': role})
                return dialog_response(request, form, '', url, saved=True)
    return dialog_response(request, form, 'Zmień rolę w zespole' if member else 'Dodaj osobę do zespołu', url)


@login_required
@require_POST
def remove_member(request, pk, member_pk):
    team = get_object_or_404(teams_for(request), pk=pk)
    if not manage_team(request, team):
        raise PermissionDenied
    with transaction.atomic():
        Workplace.objects.select_for_update().get(pk=request.workplace.pk)
        team = get_object_or_404(teams_for(request).select_for_update(), pk=pk)
        if not manage_team(request, team):
            raise PermissionDenied
        member = get_object_or_404(team.memberships, pk=member_pk)
        if administrators(request, team).filter(pk=member.pk).exists() and administrators(request, team).count() == 1:
            if getattr(request, '_react_api', False):
                from core.api import api_error
                return api_error('Zespół musi mieć co najmniej jednego aktywnego administratora.', 400)
            messages.error(request, 'Zespół musi mieć co najmniej jednego aktywnego administratora.')
        else:
            member.delete()
    return redirect(app_url(request, f'{pk}/?view=members', 'teams'))


@login_required
@require_http_methods(['GET', 'POST'])
def delete(request, pk):
    team = get_object_or_404(teams_for(request), pk=pk)
    if not manage_team(request, team):
        raise PermissionDenied
    form = TeamDeleteForm(request.POST if request.method == 'POST' else None, team=team)
    url = app_url(request, f'{pk}/', 'teams')
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            Workplace.objects.select_for_update().get(pk=request.workplace.pk)
            team = get_object_or_404(teams_for(request).select_for_update(), pk=pk)
            if not manage_team(request, team):
                raise PermissionDenied
            if team.name != form.cleaned_data['name']:
                form.add_error('name', 'Nazwa zespołu zmieniła się. Odśwież formularz.')
            else:
                team.delete()
                return dialog_response(request, form, '', app_url(request, app='teams'), saved=True)
    return dialog_response(request, form, 'Usuń zespół', url)


@login_required
@require_GET
def photo(request, pk):
    team = get_object_or_404(teams_for(request).exclude(photo=''), pk=pk)
    try:
        photo_file = team.photo.open('rb')
    except FileNotFoundError:
        raise Http404
    response = FileResponse(photo_file, content_type=mimetypes.guess_type(team.photo.name)[0] or 'application/octet-stream')
    response['Cache-Control'] = 'private, no-store'
    response['X-Content-Type-Options'] = 'nosniff'
    return response
