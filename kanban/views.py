from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
import json
from .models import KanbanBoard, KanbanColumn, KanbanCard
from .forms import KanbanCardForm

@login_required
def index(request):
    # Get or create a default board for the user
    board = KanbanBoard.objects.filter(user=request.user).first()
    
    if not board:
        board = KanbanBoard.objects.create(name="Moja Tablica", user=request.user)
        # Create default columns
        KanbanColumn.objects.create(board=board, name="Do zrobienia", order=1)
        KanbanColumn.objects.create(board=board, name="W toku", order=2)
        KanbanColumn.objects.create(board=board, name="Gotowe", order=3)
    
    columns = board.columns.prefetch_related('cards').all()
    form = KanbanCardForm()
    # Set the column queryset to only show columns from this board
    form.fields['column'].queryset = board.columns.all()
    
    return render(request, 'kanban/index.html', {
        'board': board,
        'columns': columns,
        'form': form
    })

@login_required
@require_POST
def create_card(request):
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.POST.get('is_ajax')
    
    # If priority is missing, default to medium
    data = request.POST.copy()
    if not data.get('priority'):
        data['priority'] = 'medium'
        
    form = KanbanCardForm(data)
    if form.is_valid():
        card = form.save(commit=False)
        card.user = request.user
        
        # Ensure the column belongs to the user's board
        if card.column.board.user != request.user:
            if is_ajax:
                return JsonResponse({'status': 'error', 'message': 'Invalid column'}, status=403)
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
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.POST.get('is_ajax')
    name = request.POST.get('name')
    board_id = request.POST.get('board_id')
    
    if name and board_id:
        board = get_object_or_404(KanbanBoard, id=board_id, user=request.user)
        last_column = board.columns.order_by('-order').first()
        order = (last_column.order + 1) if last_column else 0
        column = KanbanColumn.objects.create(board=board, name=name, order=order)
        
        if is_ajax:
            return JsonResponse({
                'status': 'success', 
                'column_id': column.id,
                'name': column.name
            })
            
    return redirect('kanban:index')

@login_required
@require_POST
def update_card(request, card_id):
    try:
        data = json.loads(request.body)
        card = get_object_or_404(KanbanCard, id=card_id, user=request.user)
        
        if 'title' in data:
            card.title = data['title']
        if 'description' in data:
            card.description = data['description']
        if 'priority' in data:
            card.priority = data['priority']
            
        card.save()
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@login_required
@require_POST
def move_card(request):
    try:
        data = json.loads(request.body)
        card_id = data.get('card_id')
        column_id = data.get('column_id')
        new_order = data.get('order')
        
        card = KanbanCard.objects.get(id=card_id, user=request.user)
        new_column = KanbanColumn.objects.get(id=column_id, board__user=request.user)
        
        card.column = new_column
        card.order = new_order
        card.save()
        
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@login_required
def card_detail(request, card_id):
    card = get_object_or_404(KanbanCard, id=card_id, user=request.user)
    return JsonResponse({
        'id': card.id,
        'title': card.title,
        'description': card.description,
        'priority': card.priority,
        'priority_display': card.get_priority_display(),
        'column_name': card.column.name,
        'is_completed': card.is_completed,
        'created_at': card.created_at.strftime('%d.%m.%Y %H:%M'),
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
        column_id = data.get('column_id')
        card_ids = data.get('card_ids', [])
        
        column = get_object_or_404(KanbanColumn, id=column_id, board__user=request.user)
        
        for index, card_id in enumerate(card_ids):
            KanbanCard.objects.filter(id=card_id, user=request.user).update(column=column, order=index)
            
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@login_required
@require_POST
def reorder_columns(request):
    try:
        data = json.loads(request.body)
        column_ids = data.get('column_ids', [])
        
        for index, column_id in enumerate(column_ids):
            KanbanColumn.objects.filter(id=column_id, board__user=request.user).update(order=index)
            
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@login_required
@require_POST
def update_column_name(request, column_id):
    try:
        data = json.loads(request.body)
        name = data.get('name')
        if not name:
            return JsonResponse({'status': 'error', 'message': 'Name is required'}, status=400)
            
        column = get_object_or_404(KanbanColumn, id=column_id, board__user=request.user)
        column.name = name
        column.save()
        
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

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
