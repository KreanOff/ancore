import os
from urllib.parse import urlencode

from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.http import JsonResponse
from django.urls import reverse

from .models import (
    Workspace,
    KanbanBoard,
    BOARD_BACKGROUND_CHOICES,
)

RECENT_BOARDS_SESSION_KEY = 'kanban_recent_boards'
RECENT_BOARDS_LIMIT = 8

BOARD_BACKGROUND_MAX_BYTES = 5 * 1024 * 1024
BOARD_BACKGROUND_ALLOWED_TYPES = {
    'image/jpeg', 'image/png', 'image/webp', 'image/gif',
}
BOARD_BACKGROUND_ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}

PLACEHOLDER = '__ID__'


def json_error(message, status=400):
    return JsonResponse({'status': 'error', 'message': message}, status=status)


def board_background_json(board):
    return {
        'status': 'success',
        'background': board.background,
        'background_style': board.background_style,
        'background_source': board.background_source,
        'has_custom': board.has_custom_background,
        'background_url': board.background_url or '',
        'image_url': board.background_image.url if board.background_image else '',
    }


def validate_background_url(url):
    url = url.strip()
    if not url:
        raise ValidationError('Podaj adres URL obrazu')
    if any(char in url for char in ('"', "'", '(', ')', '\\')):
        raise ValidationError('Nieprawidłowy adres URL')
    validator = URLValidator(schemes=['http', 'https'])
    validator(url)
    return url


def track_recent_board(request, board_id):
    if not board_id:
        return
    recent = request.session.get(RECENT_BOARDS_SESSION_KEY, [])
    board_id = int(board_id)
    recent = [bid for bid in recent if bid != board_id]
    recent.insert(0, board_id)
    request.session[RECENT_BOARDS_SESSION_KEY] = recent[:RECENT_BOARDS_LIMIT]
    request.session.modified = True


def ensure_default_workspace(user):
    if Workspace.objects.filter(user=user).exists():
        workspace = Workspace.objects.filter(user=user).order_by('created_at').first()
        KanbanBoard.objects.filter(user=user, workspace__isnull=True).update(workspace=workspace)
        return
    workspace = Workspace.objects.create(name="Moja Przestrzeń", user=user)
    KanbanBoard.objects.filter(user=user, workspace__isnull=True).update(workspace=workspace)


def board_index_url(workspace_id=None, board_id=None):
    base = reverse('kanban:index')
    params = {}
    if workspace_id:
        params['workspace_id'] = workspace_id
    if board_id:
        params['board_id'] = board_id
    if not params:
        return base
    return f'{base}?{urlencode(params)}'


def get_recent_boards(user, recent_ids):
    if not recent_ids:
        return []
    boards_by_id = {
        b.id: b
        for b in KanbanBoard.objects.filter(
            id__in=recent_ids,
            user=user,
            workspace__isnull=False,
        ).select_related('workspace')
    }
    return [boards_by_id[bid] for bid in recent_ids if bid in boards_by_id]


def _url_with_placeholder(view_name, param_name):
    path = reverse(view_name, kwargs={param_name: 0})
    return path.replace('/0/', f'/{PLACEHOLDER}/')


def build_kanban_client_urls():
    return {
        'index': reverse('kanban:index'),
        'reorderColumns': reverse('kanban:reorder_columns'),
        'reorderCards': reverse('kanban:reorder_cards'),
        'createCard': reverse('kanban:create_card'),
        'createColumn': reverse('kanban:create_column'),
        'columnUpdateName': _url_with_placeholder('kanban:update_column_name', 'column_id'),
        'columnDelete': _url_with_placeholder('kanban:delete_column', 'column_id'),
        'cardDetail': _url_with_placeholder('kanban:card_detail', 'card_id'),
        'cardUpdate': _url_with_placeholder('kanban:update_card', 'card_id'),
        'cardDelete': _url_with_placeholder('kanban:delete_card', 'card_id'),
        'cardToggle': _url_with_placeholder('kanban:toggle_card_complete', 'card_id'),
        'cardUploadAttachment': _url_with_placeholder('kanban:upload_attachment', 'card_id'),
        'attachmentDelete': _url_with_placeholder('kanban:delete_attachment', 'attachment_id'),
        'boardBackground': _url_with_placeholder('kanban:update_board_background', 'board_id'),
        'boardBackgroundUpload': _url_with_placeholder('kanban:upload_board_background', 'board_id'),
        'boardRename': _url_with_placeholder('kanban:rename_board', 'board_id'),
        'workspaceRename': _url_with_placeholder('kanban:rename_workspace', 'workspace_id'),
    }


def build_kanban_client_config(request, board):
    from django.middleware.csrf import get_token

    return {
        'csrfToken': get_token(request),
        'boardId': board.id,
        'urls': build_kanban_client_urls(),
    }


def delete_attachment_file(attachment):
    if attachment.file and os.path.isfile(attachment.file.path):
        os.remove(attachment.file.path)


def valid_board_background_keys():
    return {choice[0] for choice in BOARD_BACKGROUND_CHOICES}
