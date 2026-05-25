from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Case, Count, IntegerField, Prefetch, Q, Value, When
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.contrib import messages
import json
from ..models import Task, TaskAttachment, TaskProject, TaskSection
from ..forms import QuickTaskForm, TaskForm, TaskModalForm, TaskProjectForm, TaskProjectRenameForm, TaskSectionForm, TaskSectionRenameForm

@login_required
def tasks(request):
    return _tasks_page(request)


@login_required
def task_group(request, section_id):
    active_section = get_object_or_404(TaskSection, id=section_id, project__user=request.user)
    return _tasks_page(request, active_section=active_section)


def _tasks_page(request, active_section=None):
    project_form = TaskProjectForm()
    section_form = TaskSectionForm()
    active_project_id = request.POST.get('project_id') if request.method == 'POST' else request.GET.get('project')
    if active_section:
        active_project_id = active_section.project_id
    active_project_for_form = None
    if active_project_id:
        active_project_for_form = TaskProject.objects.filter(id=active_project_id, user=request.user).first()
    task_modal_form = TaskModalForm(user=request.user, project=active_project_for_form, section=active_section)
    project_modal_open = False
    project_rename_modal_open = False
    project_rename_form = TaskProjectRenameForm()
    project_rename_project_id = ''
    section_create_modal_open = False
    section_create_project_id = active_project_id or ''
    section_rename_modal_open = False
    section_rename_form = TaskSectionRenameForm()
    section_rename_section_id = ''
    task_modal_open = False

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'create_project':
            project_form = TaskProjectForm(request.POST)
            if project_form.is_valid():
                with transaction.atomic():
                    project = project_form.save(commit=False)
                    project.user = request.user
                    project.save()
                    TaskSection.objects.create(
                        project=project,
                        title='Nowa Grupa',
                        kind='custom',
                        order=0,
                    )
                messages.success(request, 'Projekt dodany.')
                return redirect(f"{reverse('tasks:tasks')}?project={project.id}")
            project_modal_open = True
            messages.error(request, 'Nie udało się dodać projektu.')

        if action == 'delete_project':
            project = get_object_or_404(TaskProject, id=request.POST.get('project_id'), user=request.user)
            task_count = Task.objects.filter(section__project=project, user=request.user).count()
            project.delete()
            if task_count:
                messages.success(request, 'Projekt usunięty. Zadania przeniesiono do sekcji „Bez projektu”.')
            else:
                messages.success(request, 'Projekt usunięty.')
            return redirect('tasks:tasks')

        if action in ('edit_project', 'rename_project'):
            project = get_object_or_404(TaskProject, id=request.POST.get('project_id'), user=request.user)
            project_rename_form = TaskProjectRenameForm(request.POST, instance=project)
            if project_rename_form.is_valid():
                project_rename_form.save()
                messages.success(request, 'Projekt zaktualizowany.')
                return redirect(f"{reverse('tasks:tasks')}?project={project.id}")
            project_rename_modal_open = True
            project_rename_project_id = project.id
            active_project_for_form = project
            messages.error(request, 'Nie udało się zaktualizować projektu.')

        if action == 'create_section':
            project = get_object_or_404(TaskProject, id=request.POST.get('project_id'), user=request.user)
            section_form = TaskSectionForm(request.POST)
            if section_form.is_valid():
                section = section_form.save(commit=False)
                section.project = project
                section.order = project.sections.count()
                section.save()
                messages.success(request, 'Grupa dodana.')
                return redirect('tasks:task_group', section_id=section.id)
            section_create_modal_open = True
            section_create_project_id = project.id
            messages.error(request, 'Nie udało się dodać grupy.')

        if action in ('edit_section', 'rename_section'):
            section = get_object_or_404(TaskSection, id=request.POST.get('section_id'), project__user=request.user)
            section_rename_form = TaskSectionRenameForm(request.POST, instance=section)
            if section_rename_form.is_valid():
                section_rename_form.save()
                messages.success(request, 'Grupa zaktualizowana.')
                return redirect('tasks:task_group', section_id=section.id)
            section_rename_modal_open = True
            section_rename_section_id = section.id
            active_section = section
            active_project_for_form = section.project
            messages.error(request, 'Nie udało się zaktualizować grupy.')

        if action == 'delete_section':
            section = get_object_or_404(TaskSection, id=request.POST.get('section_id'), project__user=request.user)
            project_id = section.project_id
            task_count = Task.objects.filter(section=section, user=request.user).count()
            section.delete()
            if task_count:
                messages.success(request, 'Grupa usunięta. Zadania przeniesiono do sekcji „Bez projektu”.')
            else:
                messages.success(request, 'Grupa usunięta.')
            return redirect(f"{reverse('tasks:tasks')}?project={project_id}")

        if action == 'create_task':
            section = get_object_or_404(TaskSection, id=request.POST.get('section_id'), project__user=request.user)
            form = QuickTaskForm(request.POST)
            if form.is_valid():
                task = form.save(commit=False)
                task.user = request.user
                task.section = section
                task.save()
                messages.success(request, 'Zadanie dodane.')
                return redirect('tasks:task_group', section_id=section.id)
            messages.error(request, 'Nie udało się dodać zadania.')

        if action == 'create_task_modal':
            project = None
            project_id = request.POST.get('project_id')
            if project_id:
                project = get_object_or_404(TaskProject, id=project_id, user=request.user)
            task_modal_form = TaskModalForm(request.POST, user=request.user, project=project, section=active_section)
            if task_modal_form.is_valid():
                task = task_modal_form.save(commit=False)
                task.user = request.user
                task.save()
                messages.success(request, 'Zadanie dodane.')
                return redirect('tasks:task_group', section_id=task.section_id)
            task_modal_open = True
            messages.error(request, 'Nie udało się dodać zadania.')

    tasks_qs = Task.objects.filter(user=request.user).select_related('section', 'section__project').annotate(
        is_closed_sort=Case(
            When(status='closed', then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        )
    ).order_by('is_closed_sort', 'task_id')

    projects = list(TaskProject.objects.filter(user=request.user).annotate(
        total_tasks=Count('sections__tasks', filter=Q(sections__tasks__user=request.user))
    ).prefetch_related(
        Prefetch('sections', queryset=TaskSection.objects.prefetch_related(
            Prefetch('tasks', queryset=tasks_qs)
        ))
    ))

    active_project = active_section.project if active_section else None
    if active_section:
        for project in projects:
            if project.id != active_section.project_id:
                continue
            active_project = project
            active_section = next((section for section in project.sections.all() if section.id == active_section.id), active_section)
            break

    active_project_id = request.GET.get('project') if not active_section else str(active_section.project_id)
    if active_project_id and not active_project:
        active_project = next((project for project in projects if str(project.id) == active_project_id), None)

    orphan_tasks = tasks_qs.filter(section__isnull=True)
    if active_section:
        can_create_issue = True
    elif active_project:
        can_create_issue = active_project.sections.exists()
    else:
        can_create_issue = TaskSection.objects.filter(project__user=request.user).exists()

    context = {
        'projects': projects,
        'active_project': active_project,
        'active_section': active_section,
        'visible_sections': [active_section] if active_section else [],
        'orphan_tasks': orphan_tasks,
        'tasks': tasks_qs,
        'total_task_count': tasks_qs.count(),
        'project_form': project_form,
        'project_rename_form': project_rename_form,
        'project_rename_project_id': project_rename_project_id,
        'section_form': section_form,
        'section_create_modal_open': section_create_modal_open,
        'section_create_project_id': section_create_project_id,
        'section_rename_form': section_rename_form,
        'section_rename_section_id': section_rename_section_id,
        'section_rename_modal_open': section_rename_modal_open,
        'task_modal_form': task_modal_form,
        'quick_task_form': QuickTaskForm(),
        'project_modal_open': project_modal_open,
        'project_rename_modal_open': project_rename_modal_open,
        'task_modal_open': task_modal_open,
        'can_create_issue': can_create_issue,
    }
    return render(request, 'tasks/tasks.html', context)

@login_required
def create_task(request):
    if request.method == 'POST':
        files = request.FILES.getlist('attachments')
        form = TaskForm(request.POST, request.FILES, user=request.user)
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
        form = TaskForm(user=request.user)

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
        form = TaskForm(request.POST, request.FILES, instance=task, user=request.user)
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
        form = TaskForm(instance=task, user=request.user)

    return render(request, 'tasks/edit_task.html', {'form': form, 'task': task})

@login_required
def view_task(request, task_id):
    task = get_object_or_404(Task, task_id=task_id, user=request.user)
    all_tasks = Task.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'tasks/view_task.html', {'task': task, 'all_tasks': all_tasks})
