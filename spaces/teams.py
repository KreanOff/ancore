import mimetypes

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from workplaces.models import Workplace
from workplaces.services import workplace_people, workspace_owner
from .forms import MemberForm, TeamForm
from .models import Team, TeamMembership
from .services import app_url, space_url, manage_team, teams_for, visible_items, visible_spaces
from .views import base_context, decorate_items, dialog_response


@login_required
@require_GET
def index(request):
    query = request.GET.get('q', '').strip()[:120]
    teams = teams_for(request)
    tab = request.GET.get('tab', 'all')
    if query:
        teams = teams.filter(name__icontains=query)
    if tab == 'mine':
        teams = teams.filter(members=request.user)
    page = Paginator(teams, 30).get_page(request.GET.get('page'))
    people = workplace_people(request.workplace)
    for team in page:
        team.url = app_url(request, f'{team.pk}/', 'teams')
        team.member_count = team.members.filter(pk__in=people).count()
        team.photo_url = app_url(request, f'{team.pk}/photo/', 'teams') if team.photo else ''
    return render(request, 'spaces/teams.html', {**base_context(request), 'page': page, 'query': query, 'tab': tab, 'create_url': app_url(request, 'create/', 'teams')})


@login_required
@require_GET
def detail(request, pk):
    team = get_object_or_404(teams_for(request), pk=pk)
    spaces = visible_spaces(request).filter(teams=team)
    for space in spaces:
        space.url = space_url(request, space)
    page = Paginator(visible_items(request).filter(team=team), 50).get_page(request.GET.get('page'))
    base = app_url(request, f'{pk}/', 'teams')
    return render(request, 'spaces/team.html', {**base_context(request), 'team': team, 'team_url': base, 'edit_url': base + 'edit/', 'member_url': base + 'members/', 'photo_url': base + 'photo/' if team.photo else '', 'can_manage': manage_team(request, team), 'members': team.memberships.filter(user__in=workplace_people(request.workplace)).select_related('user'), 'spaces': spaces, 'items': decorate_items(request, page.object_list), 'page': page})


@login_required
@require_http_methods(['GET', 'POST'])
def edit(request, pk=None):
    team = get_object_or_404(teams_for(request), pk=pk) if pk else None
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
                if pk:
                    team = Team.objects.select_for_update().get(pk=pk)
                    if not manage_team(request, team):
                        raise PermissionDenied
                if Team.objects.filter(workplace=request.workplace, name__iexact=data['name']).exclude(pk=pk).exists():
                    form.add_error('name', 'Zespół o tej nazwie już istnieje.')
                    return dialog_response(request, form, 'Edytuj zespół' if pk else 'Utwórz zespół', url)
                if team is None:
                    team = Team(owner=workspace_owner(request), workplace=request.workplace, created_by=request.user)
                old_photo = team.photo.name
                team.name, team.description = data['name'], data['description']
                if data.get('photo'):
                    team.photo.save(data['photo'].name, data['photo'], save=False)
                    saved_photo = (team.photo.storage, team.photo.name)
                team.save()
                if old_photo and saved_photo:
                    transaction.on_commit(lambda storage=team.photo.storage, name=old_photo: storage.delete(name), robust=True)
                if not pk:
                    TeamMembership.objects.create(team=team, user=request.user, role='admin')
                # Hidden spaces cannot be removed or discovered by editing a team.
                visible = visible_spaces(request)
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
def members(request, pk):
    team = get_object_or_404(teams_for(request), pk=pk)
    if not manage_team(request, team):
        raise PermissionDenied
    form = MemberForm(request.POST if request.method == 'POST' else None, request=request, team=True)
    url = app_url(request, f'{pk}/', 'teams')
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            Workplace.objects.select_for_update().get(pk=request.workplace.pk)
            Team.objects.select_for_update().get(pk=team.pk)
            if not manage_team(request, team):
                raise PermissionDenied
            person, role = form.cleaned_data['person'], form.cleaned_data['role']
            old = team.memberships.filter(user=person).first()
            if old and old.role == 'admin' and role != 'admin' and team.memberships.filter(role='admin', user__in=workplace_people(request.workplace)).count() == 1:
                form.add_error('role', 'Zespół musi mieć co najmniej jednego aktywnego administratora.')
            elif not workplace_people(request.workplace).filter(pk=person.pk).exists():
                form.add_error('person', 'Ta osoba nie należy już do Workspace.')
            else:
                TeamMembership.objects.update_or_create(team=team, user=person, defaults={'role': role})
                return dialog_response(request, form, '', url, saved=True)
    return dialog_response(request, form, 'Dodaj osobę / zmień rolę', url)


@login_required
@require_POST
def remove_member(request, pk, member_pk):
    team = get_object_or_404(teams_for(request), pk=pk)
    if not manage_team(request, team):
        raise PermissionDenied
    with transaction.atomic():
        Team.objects.select_for_update().get(pk=team.pk)
        if not manage_team(request, team):
            raise PermissionDenied
        member = get_object_or_404(team.memberships, pk=member_pk)
        if member.role == 'admin' and team.memberships.filter(role='admin', user__in=workplace_people(request.workplace)).count() == 1:
            messages.error(request, 'Zespół musi mieć co najmniej jednego aktywnego administratora.')
        else:
            member.delete()
    return redirect(app_url(request, f'{pk}/', 'teams'))


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
