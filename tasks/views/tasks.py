from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Case, When, Value, IntegerField
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
import json
from ..models import Task, TaskAttachment
from ..forms import TaskForm

@login_required
def tasks(request):
    tasks = Task.objects.filter(user=request.user).annotate(
        is_closed_sort=Case(
            When(status='closed', then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        )
    ).order_by('is_closed_sort', '-created_at')
    
    return render(request, 'tasks/tasks.html', {'tasks': tasks})

@login_required
def create_task(request):
    if request.method == 'POST':
        files = request.FILES.getlist('attachments')
        form = TaskForm(request.POST, request.FILES)
        if form.is_valid():
            task = form.save(commit=False)
            task.user = request.user
            task.save()

            # Handle file attachments
            for file in files:
                TaskAttachment.objects.create(
                    task=task,
                    file=file
                )

            messages.success(request, 'Zadanie utworzone pomyślnie.')
            return redirect('tasks:tasks')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = TaskForm()

    return render(request, 'tasks/create_task.html', {'form': form})


@login_required
@require_POST
def update_task_status(request, task_id):
    try:
        task = Task.objects.get(task_id=task_id, user=request.user)
        data = json.loads(request.body)
        is_completed = data.get('is_completed', False)
        
        task.is_completed = is_completed
        task.status = 'closed' if is_completed else 'reopened'
        task.save()
        
        return JsonResponse({
            'status': 'success',
            'new_status_display': task.get_status_display(),
            'new_status_code': task.status
        })
    except Task.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Zadanie nie znalezione'}, status=404)

@login_required
@require_POST
def delete_task(request, task_id):
    try:
        task = Task.objects.get(task_id=task_id, user=request.user)
        task.delete()
        return JsonResponse({'status': 'success', 'message': 'Zadanie usunięte pomyślnie'})
    except Task.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Zadanie nie znalezione'}, status=404)

@login_required
@require_POST
def delete_attachment(request, attachment_id):
    try:
        attachment = get_object_or_404(TaskAttachment, id=attachment_id, task__user=request.user)
        attachment.delete()
        return JsonResponse({'status': 'success', 'message': 'Załącznik usunięty pomyślnie'})
    except TaskAttachment.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Załącznik nie znaleziony'}, status=404)

@login_required
@require_POST
def delete_tasks(request):
    try:
        data = json.loads(request.body)
        task_ids = data.get('task_ids', [])
        
        if not task_ids:
            return JsonResponse({'status': 'error', 'message': 'Nie podano ID zadań'}, status=400)
        
        user = request.user
        deleted_count = Task.objects.filter(task_id__in=task_ids, user=user).delete()[0]
        
        # Renumber remaining tasks for this user
        Task._renumber_user_tasks(user)
        
        return JsonResponse({
            'status': 'success', 
            'message': f'{deleted_count} {"zadań" if deleted_count != 1 else "zadanie"} usuniętych pomyślnie',
            'deleted_count': deleted_count
        })
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Nieprawidłowy JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
@require_POST
def bulk_update_status(request):
    try:
        data = json.loads(request.body)
        task_ids = data.get('task_ids', [])
        status = data.get('status', 'closed')
        
        if not task_ids:
            return JsonResponse({'status': 'error', 'message': 'Nie podano ID zadań'}, status=400)
        
        user = request.user
        updated_count = Task.objects.filter(task_id__in=task_ids, user=user).update(status=status)
        
        return JsonResponse({
            'status': 'success', 
            'message': f'Zaktualizowano {updated_count} {"zadań" if updated_count != 1 else "zadanie"}',
            'updated_count': updated_count
        })
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Nieprawidłowy JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

@login_required
def edit_task(request, task_id):
    task = get_object_or_404(Task, task_id=task_id, user=request.user)
    
    if request.method == 'POST':
        files = request.FILES.getlist('attachments')
        form = TaskForm(request.POST, request.FILES, instance=task)
        if form.is_valid():
            form.save()

            # Handle staged attachment deletions
            deleted_attachments = request.POST.get('deleted_attachments', '')
            if deleted_attachments:
                attachment_ids = [int(aid) for aid in deleted_attachments.split(',') if aid.isdigit()]
                TaskAttachment.objects.filter(id__in=attachment_ids, task=task).delete()

            # Handle new file attachments
            for file in files:
                TaskAttachment.objects.create(
                    task=task,
                    file=file
                )

            messages.success(request, 'Zadanie zaktualizowane pomyślnie.')
            return redirect('tasks:view-task', task_id=task.task_id)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = TaskForm(instance=task)

    return render(request, 'tasks/edit_task.html', {'form': form, 'task': task})

@login_required
def view_task(request, task_id):
    task = get_object_or_404(Task, task_id=task_id, user=request.user)
    all_tasks = Task.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'tasks/view_task.html', {'task': task, 'all_tasks': all_tasks})
