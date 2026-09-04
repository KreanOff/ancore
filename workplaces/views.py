import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Case, IntegerField, Max, Value, When
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import WorkplaceForm
from .models import SidebarFavorite, create_workplace_for_user
from .navigation import SIDEBAR_FAVORITE_KEYS, sidebar_favorites_for_request
from .services import enable_workspace_url_scope, scoped_workplace_app_path, set_active_workplace, workplaces_for_user


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
            set_active_workplace(request, workplace)
            messages.success(request, 'Miejsce pracy utworzone.')
            return redirect(scoped_workplace_app_path(workplace, 'tasks'))
        messages.error(request, 'Nie udało się utworzyć miejsca pracy.')

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
    return render(request, 'workplaces/workplaces.html', {
        'workplaces': user_workplaces,
        'form': form,
        'active_workplace': active_workplace,
        'workplace_create_modal_open': workplace_create_modal_open,
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
    form = WorkplaceForm(request.POST, request.FILES, instance=workplace, user=request.user)
    if form.is_valid():
        form.save()
        messages.success(request, 'Ustawienia miejsca pracy zapisane.')
    else:
        name_errors = form.errors.get('name')
        messages.error(
            request,
            str(name_errors[0]) if name_errors else 'Nie udało się zapisać ustawień miejsca pracy.',
        )
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
