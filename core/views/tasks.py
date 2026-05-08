from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Case, When, Value, IntegerField
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
import json
from core.models import Task
from core.forms import TaskForm

@login_required
def tasks(request):
    tasks = Task.objects.filter(user=request.user).annotate(
        is_closed_sort=Case(
            When(status='closed', then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        )
    ).order_by('is_closed_sort', '-created_at')
    
    return render(request, 'core/tasks/tasks.html', {'tasks': tasks})

@login_required
def create_task(request):
    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.user = request.user
            task.save()
            return redirect('tasks')
    else:
        form = TaskForm()
    
    return render(request, 'core/tasks/create_task.html', {'form': form})

@login_required
def view_edit_task(request, task_id):
    task = get_object_or_404(Task, id=task_id, user=request.user)
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            messages.success(request, 'Task updated successfully.')
            return redirect('view_edit_task', task_id=task.id)
    else:
        form = TaskForm(instance=task)
    
    return render(request, 'core/tasks/view_edit_task.html', {'task': task, 'form': form})

@login_required
@require_POST
def update_task_status(request, task_id):
    try:
        task = Task.objects.get(id=task_id, user=request.user)
        data = json.loads(request.body)
        is_completed = data.get('is_completed', False)
        
        task.is_completed = is_completed
        task.status = 'closed' if is_completed else 'new'
        task.save()
        
        return JsonResponse({
            'status': 'success',
            'new_status_display': task.get_status_display(),
            'new_status_code': task.status
        })
    except Task.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Task not found'}, status=404)
