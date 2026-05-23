import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, get_object_or_404
from django.views.decorators.http import require_POST

from ..forms import KanbanCardForm
from ..models import KanbanBoard, KanbanColumn, KanbanCard, KanbanAttachment
from ..utils import json_error, delete_attachment_file


@login_required
@require_POST
def create_card(request):
    is_ajax = (
        request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        or request.POST.get('is_ajax')
    )

    form = KanbanCardForm(request.POST.copy())
    if form.is_valid():
        card = form.save(commit=False)
        card.user = request.user

        if card.column.board.user != request.user:
            if is_ajax:
                return json_error('Invalid column', status=403)
            return redirect('kanban:index')

        last_card = KanbanCard.objects.filter(column=card.column).order_by('-order').first()
        card.order = (last_card.order + 1) if last_card else 0
        card.save()

        if is_ajax:
            return JsonResponse({'status': 'success', 'card_id': card.id})
        return redirect('kanban:index')

    if is_ajax:
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
    return redirect('kanban:index')


@login_required
@require_POST
def create_column(request):
    is_ajax = (
        request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        or request.POST.get('is_ajax')
    )
    name = (request.POST.get('name') or '').strip()
    board_id = request.POST.get('board_id')

    if not name or not board_id:
        if is_ajax:
            return json_error('Nazwa listy i identyfikator tablicy są wymagane')
        return redirect('kanban:index')

    board = get_object_or_404(KanbanBoard, id=board_id, user=request.user)
    last_column = board.columns.order_by('-order').first()
    order = (last_column.order + 1) if last_column else 0
    column = KanbanColumn.objects.create(board=board, name=name, order=order)

    if is_ajax:
        return JsonResponse({
            'status': 'success',
            'column_id': column.id,
            'name': column.name,
        })
    return redirect('kanban:index')


@login_required
@require_POST
def update_card(request, card_id):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return json_error('Nieprawidłowe dane')

    card = get_object_or_404(KanbanCard, id=card_id, user=request.user)

    if 'title' in data:
        card.title = data['title']
    if 'description' in data:
        card.description = data['description']

    card.save()
    return JsonResponse({'status': 'success'})


@login_required
@require_POST
def move_card(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return json_error('Nieprawidłowe dane')

    card_id = data.get('card_id')
    column_id = data.get('column_id')
    new_order = data.get('order')

    try:
        card = KanbanCard.objects.get(id=card_id, user=request.user)
        new_column = KanbanColumn.objects.get(id=column_id, board__user=request.user)
    except (KanbanCard.DoesNotExist, KanbanColumn.DoesNotExist):
        return json_error('Nie znaleziono karty lub kolumny', status=404)

    if new_column.board_id != card.column.board_id:
        return json_error('Nie można przenieść karty na inną tablicę')

    card.column = new_column
    card.order = new_order
    card.save()
    return JsonResponse({'status': 'success'})


@login_required
def card_detail(request, card_id):
    card = get_object_or_404(KanbanCard, id=card_id, user=request.user)
    attachments = card.attachments.order_by('uploaded_at')
    return JsonResponse({
        'id': card.id,
        'title': card.title,
        'description': card.description,
        'column_name': card.column.name,
        'is_completed': card.is_completed,
        'created_at': card.created_at.strftime('%d.%m.%Y %H:%M'),
        'attachments': [
            {
                'id': a.id,
                'name': a.original_name,
                'url': a.file.url,
                'uploaded_at': a.uploaded_at.strftime('%d.%m.%Y'),
                'is_image': a.is_image,
                'extension': a.file_extension,
            }
            for a in attachments
        ],
    })


@login_required
@require_POST
def toggle_card_complete(request, card_id):
    card = get_object_or_404(KanbanCard, id=card_id, user=request.user)
    card.is_completed = not card.is_completed
    card.save()
    return JsonResponse({'status': 'success', 'is_completed': card.is_completed})


@login_required
@require_POST
def reorder_cards(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return json_error('Nieprawidłowe dane')

    column_id = data.get('column_id')
    card_ids = data.get('card_ids', [])

    column = get_object_or_404(KanbanColumn, id=column_id, board__user=request.user)

    if card_ids:
        cards = KanbanCard.objects.filter(id__in=card_ids, user=request.user)
        if cards.count() != len(card_ids):
            return json_error('Nie znaleziono jednej lub więcej kart', status=404)
        if cards.exclude(column__board_id=column.board_id).exists():
            return json_error('Karta nie należy do tej tablicy')

    for index, cid in enumerate(card_ids):
        KanbanCard.objects.filter(id=cid, user=request.user).update(column=column, order=index)

    return JsonResponse({'status': 'success'})


@login_required
@require_POST
def reorder_columns(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return json_error('Nieprawidłowe dane')

    column_ids = data.get('column_ids', [])
    if not column_ids:
        return JsonResponse({'status': 'success'})

    columns = KanbanColumn.objects.filter(id__in=column_ids, board__user=request.user)
    if columns.count() != len(column_ids):
        return json_error('Nie znaleziono jednej lub więcej kolumn', status=404)

    board_ids = set(columns.values_list('board_id', flat=True))
    if len(board_ids) != 1:
        return json_error('Kolumny muszą należeć do tej samej tablicy')

    for index, column_id in enumerate(column_ids):
        KanbanColumn.objects.filter(id=column_id, board__user=request.user).update(order=index)

    return JsonResponse({'status': 'success'})


@login_required
@require_POST
def update_column_name(request, column_id):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return json_error('Nieprawidłowe dane')

    name = data.get('name')
    if not name:
        return json_error('Name is required')

    column = get_object_or_404(KanbanColumn, id=column_id, board__user=request.user)
    column.name = name
    column.save()
    return JsonResponse({'status': 'success'})


@login_required
@require_POST
def delete_card(request, card_id):
    card = get_object_or_404(KanbanCard, id=card_id, user=request.user)
    card.delete()
    return JsonResponse({'status': 'success'})


@login_required
@require_POST
def delete_column(request, column_id):
    column = get_object_or_404(KanbanColumn, id=column_id, board__user=request.user)
    column.delete()
    return JsonResponse({'status': 'success'})


@login_required
@require_POST
def upload_attachment(request, card_id):
    card = get_object_or_404(KanbanCard, id=card_id, user=request.user)
    uploaded_file = request.FILES.get('file')
    if not uploaded_file:
        return json_error('Brak pliku')

    if uploaded_file.size > 25 * 1024 * 1024:
        return json_error('Plik jest za duży (max 25 MB)')

    attachment = KanbanAttachment.objects.create(
        card=card,
        file=uploaded_file,
        original_name=uploaded_file.name,
        uploaded_by=request.user,
    )
    return JsonResponse({
        'status': 'success',
        'attachment': {
            'id': attachment.id,
            'name': attachment.original_name,
            'url': attachment.file.url,
            'uploaded_at': attachment.uploaded_at.strftime('%d.%m.%Y'),
            'is_image': attachment.is_image,
            'extension': attachment.file_extension,
        },
    })


@login_required
@require_POST
def delete_attachment(request, attachment_id):
    attachment = get_object_or_404(
        KanbanAttachment,
        id=attachment_id,
        card__user=request.user,
    )
    delete_attachment_file(attachment)
    attachment.delete()
    return JsonResponse({'status': 'success'})
