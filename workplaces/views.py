import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.core.exceptions import PermissionDenied
from django.db.models import Case, Count, IntegerField, Max, Q, Value, When
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import WorkplaceForm
from .models import SidebarFavorite, create_workplace_for_user
from .navigation import SIDEBAR_FAVORITE_KEYS, sidebar_favorites_for_request
from .services import can_manage_team, enable_workspace_url_scope, pending_invitations_for_user, scoped_workplace_app_path, set_active_workplace, workplaces_for_user, workplace_management_url
from .team_views import team_context


@login_required
def workplaces(request):
    enable_workspace_url_scope(request)
    form = WorkplaceForm(user=request.user)
    workplace_create_modal_open = False

    if request.method == 'POST':
        workplace_create_modal_open = True
        form = WorkplaceForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            workplace = create_workplace_for_user(
                request.user,
                form.cleaned_data['name'],
                workplace_photo=(
                    None
                    if form.cleaned_data.get('workplace_photo_crop')
                    else form.cleaned_data.get('workplace_photo')
                ),
                description=form.cleaned_data.get('description', ''),
                code=form.cleaned_data.get('code', ''),
            )
            if form.cleaned_data.get('workplace_photo_crop'):
                form.apply_photo(workplace)
            messages.success(request, 'Miejsce pracy utworzone.')
            return redirect(workplace_management_url(workplace, 'workspaces'))
        messages.error(request, 'Nie udało się utworzyć miejsca pracy.')

    return render_workplaces(request, form=form, workplace_create_modal_open=workplace_create_modal_open)


def render_workplaces(request, *, form=None, workplace_create_modal_open=False, team_workplace=None, invite_form=None, edit_form=None):
    pending_invitations = list(pending_invitations_for_user(request.user).select_related('workplace', 'invited_by'))
    selected_invitation_id = request.GET.get('invitation') if request.method == 'GET' else None
    invitation_index = next((index for index, invitation in enumerate(pending_invitations)
                             if str(invitation.pk) == selected_invitation_id), None)
    if selected_invitation_id is not None and invitation_index is None:
        messages.info(request, 'To zaproszenie nie jest już dostępne.')
        return redirect('workplaces:workplaces')
    invitation_index = invitation_index if invitation_index is not None else 0

    active_workplace = getattr(request, 'workplace', None)
    user_workplaces = workplaces_for_user(request.user)
    if active_workplace is not None:
        user_workplaces = user_workplaces.order_by(
            Case(
                When(pk=active_workplace.pk, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            ),
            'name',
            'id',
        )
    user_workplaces = user_workplaces.prefetch_related('memberships').annotate(
        team_member_count=Count('memberships', filter=Q(memberships__is_active=True), distinct=True),
    )
    for workplace in user_workplaces:
        role = ('owner' if workplace.owner_id == request.user.pk else next(
            (member.role for member in workplace.memberships.all()
             if member.user_id == request.user.pk and member.is_active), ''
        ))
        workplace.can_manage_team = role in {'owner', 'admin'}
        workplace.viewer_role_label = {'owner': 'Właściciel', 'admin': 'Administrator', 'member': 'Członek'}.get(role, '')
    selected_id = str(team_workplace.pk) if team_workplace else request.GET.get('workspace')
    if selected_id is not None:
        team_workplace = next((workplace for workplace in user_workplaces if str(workplace.pk) == selected_id), None)
        if team_workplace is None:
            raise Http404
    else:
        team_workplace = next((workplace for workplace in user_workplaces if active_workplace and workplace.pk == active_workplace.pk), None)
        team_workplace = team_workplace or next(iter(user_workplaces), None)
    selected_team_context = team_context(request, team_workplace, invite_form) if team_workplace else {}
    default_view = 'received' if selected_invitation_id else ('members' if selected_id is not None else 'workspaces')
    management_view = request.GET.get('view', default_view)
    if management_view not in {'workspaces', 'members', 'invitations', 'received'}:
        management_view = default_view
    if workplace_create_modal_open:
        management_view = 'workspaces'
    if invite_form is not None:
        management_view = 'invitations'
    if edit_form is not None:
        management_view = 'invitations' if request.POST.get('view') == 'invitations' else 'workspaces'
    if management_view == 'invitations' and not selected_team_context.get('can_manage_team'):
        management_view = 'received'
    workplace_edit_modal_open = management_view in {'members', 'invitations'} or edit_form is not None
    workplace_edit_tab = (
        'main' if not workplace_edit_modal_open or request.GET.get('tab') == 'main' or edit_form is not None
        else management_view
    )
    if management_view in {'members', 'invitations'}:
        management_view = 'workspaces'
    return render(request, 'workplaces/workplaces.html', {
        'pending_invitations': pending_invitations,
        'response_invitation': pending_invitations[invitation_index] if pending_invitations else None,
        'invitation_modal_open': selected_invitation_id is not None,
        'invitation_position': invitation_index + 1,
        'previous_invitation': pending_invitations[invitation_index - 1] if invitation_index > 0 else None,
        'next_invitation': pending_invitations[invitation_index + 1] if invitation_index + 1 < len(pending_invitations) else None,
        'workplaces': user_workplaces,
        'form': form if form is not None else WorkplaceForm(user=request.user),
        'active_workplace': active_workplace,
        'workplace_create_modal_open': workplace_create_modal_open,
        'workplace_edit_modal_open': workplace_edit_modal_open,
        'workplace_edit_tab': workplace_edit_tab,
        'edit_form': edit_form,
        **selected_team_context,
        'management_view': management_view,
        'show_invitations': workplace_edit_tab == 'invitations',
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
@require_POST
def toggle_sidebar_favorite(request, workplace_id):
    workplace = get_object_or_404(workplaces_for_user(request.user), pk=workplace_id)
    item_key = (request.POST.get('item_key') or '').strip()
    action = (request.POST.get('favorite_action') or '').strip()

    if item_key not in SIDEBAR_FAVORITE_KEYS or action not in {'add', 'remove'}:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'Nieprawidłowa pozycja Favorites.'}, status=400)
        messages.error(request, 'Nie udało się zmienić Favorites.')
    elif action == 'add':
        next_position = (
            SidebarFavorite.objects.filter(user=request.user, workplace=workplace)
            .aggregate(max_position=Max('position'))['max_position']
        )
        SidebarFavorite.objects.get_or_create(
            user=request.user,
            workplace=workplace,
            item_key=item_key,
            defaults={'position': (next_position if next_position is not None else -1) + 1},
        )
    else:
        SidebarFavorite.objects.filter(
            user=request.user,
            workplace=workplace,
            item_key=item_key,
        ).delete()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        favorite_keys = list(
            SidebarFavorite.objects.filter(user=request.user, workplace=workplace)
            .values_list('item_key', flat=True)
        )
        favorites = sidebar_favorites_for_request(request, workplace, favorite_keys)
        html = render_to_string(
            'workplaces/includes/sidebar_favorites.html',
            {
                'current_workplace': workplace,
                'sidebar_favorites': favorites,
                'sidebar_next_url': request.POST.get('next') or scoped_workplace_app_path(workplace, 'tasks'),
            },
            request=request,
        )
        return JsonResponse({
            'status': 'success',
            'item_key': item_key,
            'is_favorite': item_key in favorite_keys,
            'html': html,
        })

    next_url = request.POST.get('next') or ''
    if not url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        next_url = scoped_workplace_app_path(workplace, 'tasks')
    return redirect(next_url)


@login_required
@require_POST
def reorder_sidebar_favorites(request, workplace_id):
    workplace = get_object_or_404(workplaces_for_user(request.user), pk=workplace_id)

    try:
        item_order = json.loads(request.POST.get('item_order') or '[]')
    except (TypeError, json.JSONDecodeError):
        item_order = None

    if (
        not isinstance(item_order, list)
        or any(not isinstance(item_key, str) for item_key in item_order)
        or len(item_order) != len(set(item_order))
        or any(item_key not in SIDEBAR_FAVORITE_KEYS for item_key in item_order)
    ):
        return _sidebar_favorite_reorder_error(request, workplace)

    with transaction.atomic():
        favorites = list(
            SidebarFavorite.objects.select_for_update().filter(
                user=request.user,
                workplace=workplace,
                item_key__in=SIDEBAR_FAVORITE_KEYS,
            )
        )
        favorites_by_key = {favorite.item_key: favorite for favorite in favorites}
        if set(item_order) != set(favorites_by_key):
            return _sidebar_favorite_reorder_error(request, workplace)

        for position, item_key in enumerate(item_order):
            favorites_by_key[item_key].position = position
        SidebarFavorite.objects.bulk_update(favorites, ['position'])

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success', 'item_order': item_order})

    return redirect(_sidebar_favorite_next_url(request, workplace))


def _sidebar_favorite_reorder_error(request, workplace):
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse(
            {'status': 'error', 'message': 'Nie udało się zapisać kolejności Favorites.'},
            status=400,
        )
    messages.error(request, 'Nie udało się zapisać kolejności Favorites.')
    return redirect(_sidebar_favorite_next_url(request, workplace))


def _sidebar_favorite_next_url(request, workplace):
    next_url = request.POST.get('next') or ''
    if not url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return scoped_workplace_app_path(workplace, 'tasks')
    return next_url


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
    if not can_manage_team(request.user, workplace):
        raise PermissionDenied
    form = WorkplaceForm(request.POST, request.FILES, instance=workplace, user=workplace.owner)
    if form.is_valid():
        form.save()
        messages.success(request, 'Ustawienia miejsca pracy zapisane.')
    else:
        return render_workplaces(request, team_workplace=workplace, edit_form=form)
    return redirect(workplace_management_url(workplace, request.POST.get('view')))


@login_required
@require_POST
def delete_workplace(request, workplace_id):
    workplaces = workplaces_for_user(request.user).filter(owner=request.user)
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
