import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from ..forms import KanbanCardForm
from ..models import (
    Workspace,
    KanbanBoard,
    KanbanColumn,
    BOARD_BACKGROUND_CHOICES,
    BOARD_BACKGROUND_STYLES,
    random_board_background,
)
from ..utils import (
    RECENT_BOARDS_SESSION_KEY,
    ensure_default_workspace,
    track_recent_board,
    board_index_url,
    get_recent_boards,
    build_kanban_client_config,
    json_error,
)


@login_required
def workspaces(request):
    ensure_default_workspace(request.user)

    workspaces_qs = (
        Workspace.objects.filter(user=request.user)
        .prefetch_related('boards')
        .order_by('created_at')
    )

    recent_ids = request.session.get(RECENT_BOARDS_SESSION_KEY, [])
    recent_boards = get_recent_boards(request.user, recent_ids)

    return render(request, 'kanban/workspaces.html', {
        'workspaces': workspaces_qs,
        'recent_boards': recent_boards,
    })


@login_required
def index(request):
    ensure_default_workspace(request.user)

    workspace_id = request.GET.get('workspace_id')
    active_workspace = None
    if workspace_id:
        active_workspace = Workspace.objects.filter(id=workspace_id, user=request.user).first()
    if not active_workspace:
        active_workspace = Workspace.objects.filter(user=request.user).first()

    board_id = request.GET.get('board_id')
    board = None
    if board_id:
        board = KanbanBoard.objects.filter(
            id=board_id, workspace=active_workspace, user=request.user,
        ).first()
    if not board:
        board = KanbanBoard.objects.filter(
            workspace=active_workspace, user=request.user,
        ).first()

    if not board:
        board = KanbanBoard.objects.create(
            name="Główna Tablica",
            workspace=active_workspace,
            user=request.user,
            background=random_board_background(),
        )
        KanbanColumn.objects.create(board=board, name="Do zrobienia", order=1)
        KanbanColumn.objects.create(board=board, name="W toku", order=2)
        KanbanColumn.objects.create(board=board, name="Gotowe", order=3)

    track_recent_board(request, board.id)

    workspaces = Workspace.objects.filter(user=request.user).order_by('created_at')
    boards = KanbanBoard.objects.filter(
        workspace=active_workspace, user=request.user,
    ).order_by('created_at')

    columns = board.columns.prefetch_related('cards').all()
    form = KanbanCardForm()
    form.fields['column'].queryset = board.columns.all()

    board_backgrounds = [
        {'key': key, 'label': label, 'style': BOARD_BACKGROUND_STYLES[key]}
        for key, label in BOARD_BACKGROUND_CHOICES
    ]

    return render(request, 'kanban/index.html', {
        'workspaces': workspaces,
        'active_workspace': active_workspace,
        'boards': boards,
        'board': board,
        'columns': columns,
        'form': form,
        'board_backgrounds': board_backgrounds,
        'kanban_config': build_kanban_client_config(request, board),
    })


@login_required
@require_POST
def create_workspace(request):
    name = request.POST.get('name', '').strip()
    if not name:
        name = "Nowa Przestrzeń"
    workspace = Workspace.objects.create(name=name, user=request.user)
    board = KanbanBoard.objects.create(
        name="Główna Tablica",
        workspace=workspace,
        user=request.user,
        background=random_board_background(),
    )
    KanbanColumn.objects.create(board=board, name="Do zrobienia", order=1)
    KanbanColumn.objects.create(board=board, name="W toku", order=2)
    KanbanColumn.objects.create(board=board, name="Gotowe", order=3)
    return redirect('kanban:workspaces')


@login_required
@require_POST
def rename_workspace(request, workspace_id):
    workspace = get_object_or_404(Workspace, id=workspace_id, user=request.user)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return json_error('Nieprawidłowe dane')
    name = data.get('name', '').strip()
    if not name:
        return json_error('Name is required')
    workspace.name = name
    workspace.save()
    return JsonResponse({'status': 'success'})


@login_required
@require_POST
def delete_workspace(request, workspace_id):
    workspace = get_object_or_404(Workspace, id=workspace_id, user=request.user)
    workspace.delete()
    remaining = Workspace.objects.filter(user=request.user).order_by('created_at').first()
    if remaining:
        return redirect(board_index_url(workspace_id=remaining.id))
    return redirect('kanban:index')
