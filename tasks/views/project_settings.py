from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Max
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from ..forms import TaskProjectDeadlineRuleForm, TaskProjectFieldOptionForm
from ..models import TaskProject, TaskProjectDeadlineRule, TaskProjectFieldOption
from .tasks import _active_workplace, _project_field_configuration


def _save_deadline_settings(request, workplace, project_id, default_rules):
    action = request.POST.get('action')
    with transaction.atomic():
        project = None
        if project_id:
            project = get_object_or_404(
                TaskProject.objects.select_for_update().filter(user=request.user, workplace=workplace),
                pk=project_id,
            )
        scoped_rules = TaskProjectDeadlineRule.for_scope(request.user, workplace, project)
        if action == 'enable_project_deadline_rules':
            if project is None:
                raise PermissionDenied
            if not project.use_custom_deadline_rules:
                scoped_rules.delete()
                TaskProjectDeadlineRule.objects.bulk_create([
                    TaskProjectDeadlineRule(
                        owner=request.user, workplace=workplace, project=project,
                        days=rule.days, color=rule.color,
                    )
                    for rule in default_rules
                ])
                project.use_custom_deadline_rules = True
                project.save(update_fields=['use_custom_deadline_rules'])
            messages.success(request, 'Włączono własne progi terminu dla projektu.')
        elif action == 'reset_project_deadline_rules':
            if project is None:
                raise PermissionDenied
            project.use_custom_deadline_rules = False
            project.save(update_fields=['use_custom_deadline_rules'])
            scoped_rules.delete()
            messages.success(request, 'Projekt korzysta teraz ze wspólnych progów terminu.')
        else:
            if project and not project.use_custom_deadline_rules:
                raise PermissionDenied
            if action == 'create_project_deadline_rule':
                rule = TaskProjectDeadlineRule(owner=request.user, workplace=workplace, project=project)
            else:
                rule = get_object_or_404(scoped_rules.filter(is_active=True), id=request.POST.get('rule_id'))
            if action == 'delete_project_deadline_rule':
                rule.is_active = False
                rule.save(update_fields=['is_active'])
                messages.success(request, 'Usunięto regułę terminu.')
            else:
                rule_form = TaskProjectDeadlineRuleForm(request.POST, instance=rule)
                if rule_form.is_valid():
                    rule_form.save()
                    messages.success(request, 'Zapisano regułę terminu.')
                else:
                    messages.error(request, ' '.join(
                        str(error) for errors in rule_form.errors.values() for error in errors
                    ))
    url = reverse('project_field_settings')
    if project:
        url += f'?project_id={project.pk}'
    return redirect(f'{url}#project-field-group-deadline')


@login_required
@require_http_methods(['GET', 'POST'])
def project_field_settings(request):
    workplace = _active_workplace(request)
    configuration = _project_field_configuration(request.user, workplace)
    projects = TaskProject.objects.filter(user=request.user, workplace=workplace).order_by('name', 'id')
    project_id = (request.POST if request.method == 'POST' else request.GET).get('project_id')
    if project_id:
        try:
            project_id = int(project_id)
            if project_id <= 0:
                raise ValueError
        except (TypeError, ValueError):
            raise Http404('Nie znaleziono projektu.')
    deadline_project = get_object_or_404(projects, pk=project_id) if project_id else None

    if request.method == 'POST':
        action = request.POST.get('action')

        if action in (
            'create_project_deadline_rule', 'update_project_deadline_rule', 'delete_project_deadline_rule',
            'enable_project_deadline_rules', 'reset_project_deadline_rules',
        ):
            return _save_deadline_settings(request, workplace, project_id, configuration['deadline_rules'])

        if action == 'create_project_field_option':
            field_type = (request.POST.get('field_type') or '').strip()
            if field_type not in dict(TaskProjectFieldOption.FIELD_CHOICES):
                raise PermissionDenied
            option = TaskProjectFieldOption(
                owner=request.user,
                workplace=workplace,
                field_type=field_type,
            )
            option_form = TaskProjectFieldOptionForm(
                request.POST,
                instance=option,
                owner=request.user,
                workplace=workplace,
            )
            if option_form.is_valid():
                option = option_form.save(commit=False)
                option.value = TaskProjectFieldOption.unique_value_for_label(
                    request.user,
                    workplace,
                    field_type,
                    option.label,
                )
                option.position = (
                    TaskProjectFieldOption.for_scope(request.user, workplace)
                    .filter(field_type=field_type)
                    .aggregate(last_position=Max('position'))['last_position']
                    or 0
                ) + 1
                option.save()
                messages.success(request, f'Dodano wartość „{option.label}”.')
            else:
                error_text = ' '.join(
                    str(error)
                    for errors in option_form.errors.values()
                    for error in errors
                )
                messages.error(request, error_text or 'Nie udało się dodać wartości.')
            return redirect('project_field_settings')

        if action == 'update_project_field_option':
            option = get_object_or_404(
                TaskProjectFieldOption.for_scope(request.user, workplace).filter(is_active=True),
                id=request.POST.get('option_id'),
            )
            option_form = TaskProjectFieldOptionForm(
                request.POST,
                instance=option,
                owner=request.user,
                workplace=workplace,
            )
            if option_form.is_valid():
                option_form.save()
                messages.success(request, f'Zapisano wartość „{option.label}”.')
            else:
                error_text = ' '.join(
                    str(error)
                    for errors in option_form.errors.values()
                    for error in errors
                )
                messages.error(request, error_text or 'Nie udało się zapisać wartości.')
            return redirect('project_field_settings')

        if action == 'delete_project_field_option':
            option = get_object_or_404(
                TaskProjectFieldOption.for_scope(request.user, workplace).filter(is_active=True),
                id=request.POST.get('option_id'),
            )
            active_count = TaskProjectFieldOption.for_scope(request.user, workplace).filter(
                field_type=option.field_type,
                is_active=True,
            ).count()
            if option.is_used:
                messages.error(
                    request,
                    f'Nie można usunąć wartości „{option.label}”, ponieważ jest używana przez projekt.',
                )
            elif active_count <= 1 and option.field_type != TaskProjectFieldOption.FIELD_SOURCE:
                messages.error(request, 'Każde pole musi mieć co najmniej jedną wartość.')
            else:
                option.is_active = False
                option.save(update_fields=['is_active'])
                messages.success(request, f'Usunięto wartość „{option.label}”.')
            return redirect('project_field_settings')

        raise PermissionDenied

    inherited = bool(deadline_project and not deadline_project.use_custom_deadline_rules)
    deadline_rules = configuration['deadline_rules']
    if deadline_project and not inherited:
        deadline_rules = list(TaskProjectDeadlineRule.for_scope(
            request.user, workplace, deadline_project,
        ).filter(is_active=True))
    return render(request, 'dashboard/project_field_settings.html', {
        'project_field_groups': configuration['groups'],
        'project_deadline_rules': deadline_rules,
        'deadline_projects': projects,
        'deadline_project': deadline_project,
        'deadline_inherited': inherited,
    })
