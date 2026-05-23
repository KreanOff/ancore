import json
import os

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import redirect, get_object_or_404
from django.views.decorators.http import require_POST

from ..models import (
    Workspace,
    KanbanBoard,
    KanbanColumn,
    random_board_background,
)
from ..utils import (
    board_index_url,
    board_background_json,
    validate_background_url,
    json_error,
    BOARD_BACKGROUND_MAX_BYTES,
    BOARD_BACKGROUND_ALLOWED_TYPES,
    BOARD_BACKGROUND_ALLOWED_EXTENSIONS,
    valid_board_background_keys,
)


@login_required
@require_POST
def create_board(request):
    workspace_id = request.POST.get('workspace_id')
    name = request.POST.get('name', '').strip()
    workspace = get_object_or_404(Workspace, id=workspace_id, user=request.user)
    if not name:
        name = "Nowa Tablica"
    board = KanbanBoard.objects.create(
        name=name,
        workspace=workspace,
        user=request.user,
        background=random_board_background(),
    )
    KanbanColumn.objects.create(board=board, name="Do zrobienia", order=1)
    KanbanColumn.objects.create(board=board, name="W toku", order=2)
    KanbanColumn.objects.create(board=board, name="Gotowe", order=3)
    return redirect(board_index_url(workspace_id=workspace.id, board_id=board.id))


@login_required
@require_POST
def update_board_background(request, board_id):
    board = get_object_or_404(KanbanBoard, id=board_id, user=request.user)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return json_error('Nieprawidłowe dane')

    if 'background_url' in data:
        try:
            url = validate_background_url(data.get('background_url', ''))
        except ValidationError as e:
            return json_error(e.messages[0])
        board.clear_custom_background()
        board.background_url = url
        board.save()
        return JsonResponse(board_background_json(board))

    background = data.get('background', '').strip()
    if background not in valid_board_background_keys():
        return json_error('Nieprawidłowa tapeta')
    board.clear_custom_background()
    board.background = background
    board.save()
    return JsonResponse(board_background_json(board))


@login_required
@require_POST
def upload_board_background(request, board_id):
    board = get_object_or_404(KanbanBoard, id=board_id, user=request.user)
    uploaded = request.FILES.get('background_image')
    if not uploaded:
        return json_error('Brak pliku')

    if uploaded.size > BOARD_BACKGROUND_MAX_BYTES:
        return json_error('Plik jest za duży (max 5 MB)')

    content_type = getattr(uploaded, 'content_type', '') or ''
    ext = os.path.splitext(uploaded.name)[1].lower()
    if (
        content_type not in BOARD_BACKGROUND_ALLOWED_TYPES
        and ext not in BOARD_BACKGROUND_ALLOWED_EXTENSIONS
    ):
        return json_error('Dozwolone formaty: JPG, PNG, WebP, GIF')

    board.clear_custom_background()
    board.background_url = ''
    board.background_image = uploaded
    board.save()
    return JsonResponse(board_background_json(board))


@login_required
@require_POST
def rename_board(request, board_id):
    board = get_object_or_404(KanbanBoard, id=board_id, user=request.user)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return json_error('Nieprawidłowe dane')
    name = data.get('name', '').strip()
    if not name:
        return json_error('Name is required')
    board.name = name
    board.save()
    return JsonResponse({'status': 'success'})


@login_required
@require_POST
def delete_board(request, board_id):
    board = get_object_or_404(KanbanBoard, id=board_id, user=request.user)
    workspace_id = board.workspace_id
    board.delete()
    if workspace_id:
        return redirect(board_index_url(workspace_id=workspace_id))
    return redirect('kanban:index')
