from collections import defaultdict

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Case, Count, IntegerField, Prefetch, Q, Value, When
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.contrib import messages
import json
from accounts.avatar import account_avatar
from accounts.models import normalize_public_username
from contacts.models import SharedItem, SharedItemLink, UserContact
from ..models import Task, TaskActivity, TaskAttachment, TaskProject, TaskSection, TaskTag
from ..forms import QuickTaskForm, SubTaskModalForm, TaskForm, TaskModalForm, TaskProjectForm, TaskProjectRenameForm, TaskSectionForm, TaskSectionRenameForm, TaskTagForm


def _status_groups_for_tasks(tasks):
    tasks_by_status = {status: [] for status, _label in Task.STATUS_CHOICES}
    for task in tasks:
        tasks_by_status.setdefault(task.status, []).append(task)
    return [
        {
            'status': status,
            'label': label,
            'tasks': tasks_by_status.get(status, []),
            'count': len(tasks_by_status.get(status, [])),
        }
        for status, label in Task.STATUS_CHOICES
    ]


def _decorate_status_groups(projects, orphan_tasks):
    for project in projects:
        project_tasks = []
        for section in project.sections.all():
            section_tasks = list(section.tasks.all())
            section.status_groups = _status_groups_for_tasks(section_tasks)
            project_tasks.extend(section_tasks)
        project.status_groups = _status_groups_for_tasks(project_tasks)
    return _status_groups_for_tasks(list(orphan_tasks))


def _sections_for_projects(projects):
    return [section for project in projects for section in project.sections.all()]


def _user_display_name(user):
    return user.get_full_name() or user.email or user.username


def _task_shared_ids(user, model):
    return SharedItem.objects.filter(
        content_type=ContentType.objects.get_for_model(model),
        shared_with=user,
    ).values_list('object_id', flat=True)


def _task_share_owner(obj):
    if isinstance(obj, TaskProject):
        return obj.user
    if isinstance(obj, TaskSection):
        return obj.project.user
    if isinstance(obj, Task):
        return obj.user
    return None


def _task_share_label(obj):
    if isinstance(obj, TaskProject):
        return obj.name
    if isinstance(obj, TaskSection):
        return obj.title
    if isinstance(obj, Task):
        return obj.title
    return str(obj)


def _task_share_type_label(obj):
    if isinstance(obj, TaskProject):
        return 'Projekt'
    if isinstance(obj, TaskSection):
        return 'Grupa'
    if isinstance(obj, Task):
        return 'Zadanie'
    return 'Element'


def _task_share_object_url(obj):
    if isinstance(obj, TaskProject):
        return f"{reverse('tasks:tasks')}?view=shared-projects"
    if isinstance(obj, TaskSection):
        return reverse('tasks:task_group', args=[obj.id])
    if isinstance(obj, Task):
        return reverse('tasks:view-shared-task', args=[obj.id])
    return reverse('tasks:tasks')


def _user_can_access_project(user, project):
    if project.user_id == user.id:
        return True
    return SharedItem.objects.filter(
        content_type=ContentType.objects.get_for_model(TaskProject),
        object_id=project.id,
        shared_with=user,
    ).exists()


def _user_can_access_section(user, section):
    if section.project.user_id == user.id:
        return True
    section_shared = SharedItem.objects.filter(
        content_type=ContentType.objects.get_for_model(TaskSection),
        object_id=section.id,
        shared_with=user,
    ).exists()
    return section_shared or _user_can_access_project(user, section.project)


def _user_can_access_task(user, task):
    if task.user_id == user.id:
        return True

    task_ids = list(_task_shared_ids(user, Task))
    if task.id in task_ids or (task.parent_id and task.parent_id in task_ids):
        return True

    if task.section_id:
        return _user_can_access_section(user, task.section)

    return False


def _task_access_filter(user):
    project_ids = list(_task_shared_ids(user, TaskProject))
    section_ids = list(_task_shared_ids(user, TaskSection))
    task_ids = list(_task_shared_ids(user, Task))

    access_filter = Q(user=user)
    if project_ids:
        access_filter |= Q(section__project_id__in=project_ids)
    if section_ids:
        access_filter |= Q(section_id__in=section_ids)
    if task_ids:
        access_filter |= Q(id__in=task_ids) | Q(parent_id__in=task_ids)
    return access_filter


def _owned_share_object(user, object_type, object_id):
    if object_type == 'project':
        return get_object_or_404(TaskProject, id=object_id, user=user)
    if object_type == 'section':
        return get_object_or_404(TaskSection, id=object_id, project__user=user)
    if object_type == 'task':
        return get_object_or_404(Task.objects.select_related('section', 'section__project'), id=object_id, user=user)
    raise PermissionDenied


def _share_link_url(request, link):
    return request.build_absolute_uri(reverse('tasks:accept-share-link', args=[link.token]))


def _decorate_share_links(request, items):
    item_list = [item for item in items if item]
    if not item_list:
        return

    grouped_items = defaultdict(list)
    for item in item_list:
        grouped_items[item.__class__].append(item)

    for model, model_items in grouped_items.items():
        links = SharedItemLink.objects.filter(
            content_type=ContentType.objects.get_for_model(model),
            object_id__in=[item.id for item in model_items],
            created_by=request.user,
            is_active=True,
        )
        links_by_object_id = {link.object_id: link for link in links}

        for item in model_items:
            link = links_by_object_id.get(item.id)
            item.share_link_url = _share_link_url(request, link) if link else ''


def _shared_tasks_queryset(user):
    project_ids = list(_task_shared_ids(user, TaskProject))
    section_ids = list(_task_shared_ids(user, TaskSection))
    task_ids = list(_task_shared_ids(user, Task))

    shared_filter = Q()
    has_filter = False
    if project_ids:
        shared_filter |= Q(section__project_id__in=project_ids)
        has_filter = True
    if section_ids:
        shared_filter |= Q(section_id__in=section_ids)
        has_filter = True
    if task_ids:
        shared_filter |= Q(id__in=task_ids) | Q(parent_id__in=task_ids)
        has_filter = True
    if not has_filter:
        return Task.objects.none()

    return Task.objects.filter(shared_filter).exclude(user=user)


def _shared_sections_queryset(user):
    project_ids = list(_task_shared_ids(user, TaskProject))
    section_ids = list(_task_shared_ids(user, TaskSection))

    shared_filter = Q()
    has_filter = False
    if project_ids:
        shared_filter |= Q(project_id__in=project_ids)
        has_filter = True
    if section_ids:
        shared_filter |= Q(id__in=section_ids)
        has_filter = True
    if not has_filter:
        return TaskSection.objects.none()

    return TaskSection.objects.filter(shared_filter).exclude(project__user=user)


def _mark_project_permissions(projects, user):
    for project in projects:
        project.can_manage = project.user_id == user.id
        project.can_share = project.can_manage
        for section in project.sections.all():
            section.can_manage = project.can_manage
            section.can_share = project.can_manage
    return projects


def _projects_for_user(user, tasks_queryset):
    shared_project_ids = list(_task_shared_ids(user, TaskProject))
    shared_section_ids = list(_task_shared_ids(user, TaskSection))

    projects_filter = Q(user=user)
    if shared_project_ids:
        projects_filter |= Q(id__in=shared_project_ids)
    if shared_section_ids:
        projects_filter |= Q(sections__id__in=shared_section_ids)

    projects = list(
        TaskProject.objects.filter(projects_filter)
        .distinct()
        .select_related('user')
        .annotate(
            total_tasks=Count(
                'sections__tasks',
                filter=Q(sections__tasks__parent__isnull=True),
            )
        )
        .prefetch_related(
            Prefetch(
                'sections',
                queryset=TaskSection.objects.select_related('project', 'project__user').prefetch_related(
                    Prefetch('tasks', queryset=tasks_queryset)
                ),
            )
        )
        .order_by('name')
    )
    return _mark_project_permissions(projects, user)


def _shared_users_by_object(content_type, object_ids):
    shared_users = defaultdict(list)
    if not object_ids:
        return shared_users

    shares = SharedItem.objects.filter(
        content_type=content_type,
        object_id__in=object_ids,
    ).select_related('shared_with').order_by('created_at', 'id')

    for share in shares:
        shared_users[share.object_id].append(share.shared_with)
    return shared_users


def _directory_member_payload(entries):
    members = []
    seen_user_ids = set()
    for entry in entries:
        if isinstance(entry, dict):
            user = entry.get('user')
            role = entry.get('role', 'Członek')
        else:
            user = entry
            role = 'Członek'
        if not user or user.pk in seen_user_ids:
            continue
        seen_user_ids.add(user.pk)
        members.append({
            'avatar': account_avatar(user),
            'label': _user_display_name(user),
            'role': role,
            'username': user.username,
            'email': user.email,
            'user_id': user.pk,
            'can_remove': entry.get('can_remove', False) if isinstance(entry, dict) else False,
            'remove_action': entry.get('remove_action', '') if isinstance(entry, dict) else '',
            'remove_project_id': entry.get('remove_project_id', '') if isinstance(entry, dict) else '',
            'remove_section_id': entry.get('remove_section_id', '') if isinstance(entry, dict) else '',
            'remove_task_id': entry.get('remove_task_id', '') if isinstance(entry, dict) else '',
            'remove_label': entry.get('remove_label', 'Przestań udostępniać') if isinstance(entry, dict) else 'Przestań udostępniać',
        })

    if not members:
        return {
            'members': [],
            'visible_members': [],
            'label': '',
            'title': '',
        }

    label = members[0]['label']

    return {
        'members': members,
        'visible_members': members[:3],
        'label': label,
        'title': ', '.join(member['label'] for member in members),
    }


def _assign_directory_members(item, users):
    payload = _directory_member_payload(users)
    item.directory_members = payload['members']
    item.directory_visible_members = payload['visible_members']
    item.directory_member_label = payload['label']
    item.directory_member_title = payload['title']


def _decorate_directory_members(projects, current_user=None):
    if not projects:
        return

    sections = _sections_for_projects(projects)
    content_types = ContentType.objects.get_for_models(TaskProject, TaskSection)
    project_shares = _shared_users_by_object(content_types[TaskProject], [project.id for project in projects])
    section_shares = _shared_users_by_object(content_types[TaskSection], [section.id for section in sections])

    for project in projects:
        shared_users = project_shares.get(project.id, [])
        can_manage_project = project.user_id == getattr(current_user, 'id', None)
        project.can_manage = can_manage_project
        project.can_share = can_manage_project
        _assign_directory_members(
            project,
            [
                {'user': project.user, 'role': 'Właściciel'},
                *(
                    {
                        'user': user,
                        'role': 'Udostępniono',
                        'can_remove': can_manage_project,
                        'remove_action': 'unshare_project',
                        'remove_project_id': project.id,
                    }
                    for user in shared_users
                ),
            ],
        )

        for section in project.sections.all():
            section.can_manage = can_manage_project
            section.can_share = can_manage_project
            _assign_directory_members(
                section,
                [
                    {'user': project.user, 'role': 'Właściciel projektu'},
                    *(
                        {
                        'user': user,
                        'role': 'Udostępniono w projekcie',
                        'can_remove': can_manage_project,
                        'remove_action': 'unshare_project',
                        'remove_project_id': project.id,
                    }
                        for user in shared_users
                    ),
                    *(
                        {
                        'user': user,
                        'role': 'Udostępniono w grupie',
                        'can_remove': can_manage_project,
                        'remove_action': 'unshare_section',
                        'remove_section_id': section.id,
                    }
                        for user in section_shares.get(section.id, [])
                    ),
                ],
            )


def _decorate_task_directory_members(tasks, current_user=None):
    task_list = [task for task in tasks if task]
    if not task_list:
        return

    content_types = ContentType.objects.get_for_models(TaskProject, TaskSection, Task)
    project_ids = [
        task.section.project_id
        for task in task_list
        if task.section_id
    ]
    section_ids = [
        task.section_id
        for task in task_list
        if task.section_id
    ]

    project_shares = _shared_users_by_object(content_types[TaskProject], project_ids)
    section_shares = _shared_users_by_object(content_types[TaskSection], section_ids)
    task_shares = _shared_users_by_object(content_types[Task], [task.id for task in task_list])

    for task in task_list:
        can_manage_task = task.user_id == getattr(current_user, 'id', None)
        task.can_manage = can_manage_task
        task.can_share = can_manage_task
        entries = [{'user': task.user, 'role': 'Właściciel'}]
        if task.section_id:
            entries.extend(
                {
                    'user': user,
                    'role': 'Udostępniono w projekcie',
                }
                for user in project_shares.get(task.section.project_id, [])
            )
            entries.extend(
                {
                    'user': user,
                    'role': 'Udostępniono w grupie',
                }
                for user in section_shares.get(task.section_id, [])
            )
        entries.extend(
            {
                'user': user,
                'role': 'Udostępniono w zadaniu',
                'can_remove': can_manage_task,
                'remove_action': 'unshare_task',
                'remove_task_id': task.id,
            }
            for user in task_shares.get(task.id, [])
        )
        _assign_directory_members(task, entries)


def _contact_matches_query(user, query):
    query_normalized = query.casefold()
    direct_matches = get_user_model().objects.filter(
        is_active=True,
        added_by_users__owner=user,
    ).exclude(pk=user.pk).filter(
        Q(first_name__icontains=query)
        | Q(middle_name__icontains=query)
        | Q(last_name__icontains=query)
        | Q(email__icontains=query)
        | Q(username__icontains=query)
    )
    contacts = list(direct_matches.distinct())

    for user_contact in UserContact.objects.filter(
        owner=user,
        target_user__is_active=True,
    ).exclude(target_user_id=user.pk).select_related('target_user', 'linked_contact'):
        target = user_contact.target_user
        linked_contact = user_contact.linked_contact
        haystack = [
            _user_display_name(target),
            target.get_full_name(),
            target.email,
            target.username,
        ]
        if linked_contact:
            haystack.extend([
                linked_contact.display_name,
                linked_contact.first_name,
                linked_contact.middle_name,
                linked_contact.last_name,
                linked_contact.email,
                linked_contact.company,
            ])
        if any(query_normalized in (value or '').casefold() for value in haystack):
            contacts.append(target)

    unique_contacts = []
    seen_user_ids = set()
    for contact in contacts:
        if contact.pk in seen_user_ids:
            continue
        seen_user_ids.add(contact.pk)
        unique_contacts.append(contact)
    return unique_contacts


def _user_name_matches_query(user, query):
    if '@' in query:
        return []

    terms = [term.strip() for term in query.split() if term.strip()]
    if not terms:
        return []

    name_filters = Q()
    for term in terms:
        name_filters &= (
            Q(first_name__icontains=term)
            | Q(middle_name__icontains=term)
            | Q(last_name__icontains=term)
        )

    return list(
        get_user_model().objects.filter(is_active=True)
        .exclude(pk=user.pk)
        .filter(name_filters)
        .order_by('first_name', 'last_name', 'email')[:25]
    )


def _share_user_options(user):
    options = []
    user_contacts = UserContact.objects.filter(
        owner=user,
        target_user__is_active=True,
    ).exclude(target_user_id=user.pk).select_related(
        'target_user',
        'linked_contact',
        'linked_contact__company_record',
    )[:100]
    for user_contact in user_contacts:
        target = user_contact.target_user
        linked_contact = user_contact.linked_contact
        linked_contact_name = ''
        if linked_contact:
            linked_contact_name = ' '.join(
                part.strip()
                for part in [linked_contact.first_name, linked_contact.middle_name, linked_contact.last_name]
                if part and part.strip()
            )
        label = linked_contact_name or target.get_full_name() or target.email or target.username
        first_name = (linked_contact.first_name if linked_contact and linked_contact.first_name else target.first_name)
        middle_name = (linked_contact.middle_name if linked_contact and linked_contact.middle_name else target.middle_name)
        last_name = (linked_contact.last_name if linked_contact and linked_contact.last_name else target.last_name)
        search_label = ' '.join(
            part.strip()
            for part in [
                first_name,
                middle_name,
                last_name,
                label,
                target.get_full_name(),
                target.email,
                target.username,
                linked_contact.email if linked_contact else '',
                linked_contact.company if linked_contact else '',
            ]
            if part and part.strip()
        )
        options.append({
            'value': target.username,
            'label': label,
            'first_name': first_name,
            'middle_name': middle_name,
            'last_name': last_name,
            'email': target.email,
            'ancore_label': target.username,
            'search_label': search_label,
            'added_at': user_contact.created_at,
            'avatar': account_avatar(target),
        })
    return options


def _tasks_next_url(request):
    fallback = reverse('tasks:tasks')
    next_url = (request.POST.get('next') or '').strip()
    if next_url == fallback or next_url.startswith(f'{fallback}?') or next_url.startswith('/tasks/'):
        return next_url
    return fallback


def _resolve_share_target(user, query):
    query = (query or '').strip()
    if not query:
        return None, 'Wpisz ID Ancore.'

    user_model = get_user_model()
    candidates = user_model.objects.filter(is_active=True).exclude(pk=user.pk)
    exact_filters = Q(username__iexact=query) | Q(username__iexact=normalize_public_username(query))

    exact_user = candidates.filter(exact_filters).first()
    if exact_user:
        return exact_user, ''

    return None, 'Nie znaleziono aktywnego użytkownika po ID Ancore.'


def _share_query_from_request(request):
    ancore_id = (request.POST.get('member_query') or '').strip()
    if ancore_id:
        return ancore_id
    return ' '.join(
        value for value in [
            (request.POST.get('member_first_name') or '').strip(),
            (request.POST.get('member_last_name') or '').strip(),
        ]
        if value
    )


def _share_task_directory_object(request, obj):
    target_user, error = _resolve_share_target(request.user, _share_query_from_request(request))
    if error:
        messages.error(request, error)
        return

    if target_user == _task_share_owner(obj):
        messages.info(request, 'Ta osoba jest już właścicielem.')
        return

    share, created = SharedItem.objects.update_or_create(
        content_type=ContentType.objects.get_for_model(obj.__class__),
        object_id=obj.pk,
        shared_by=request.user,
        shared_with=target_user,
        defaults={'permission': 'view'},
    )
    if created:
        messages.success(request, f'Dodano: {_user_display_name(target_user)}.')
    else:
        messages.info(request, f'{_user_display_name(target_user)} już jest na liście.')


def _unshare_task_directory_object(request, obj):
    target_user = get_user_model().objects.filter(pk=request.POST.get('member_id')).first()
    if not target_user:
        messages.error(request, 'Nie znaleziono użytkownika.')
        return

    deleted_count, _ = SharedItem.objects.filter(
        content_type=ContentType.objects.get_for_model(obj.__class__),
        object_id=obj.pk,
        shared_by=request.user,
        shared_with=target_user,
    ).delete()

    if deleted_count:
        messages.success(request, f'Przestano udostępniać: {_user_display_name(target_user)}.')
    else:
        messages.info(request, 'Ta osoba nie ma już dostępu z tego miejsca.')


def _posted_ids(request, plural_name, singular_name):
    ids = request.POST.getlist(plural_name)
    if not ids:
        ids = [request.POST.get(singular_name)]
    return [item for item in ids if item]


def _tasks_navigation_context(user, active_section=None, active_view=None):
    tasks_qs = Task.objects.filter(user=user, parent__isnull=True).select_related('section', 'section__project').prefetch_related('tags').annotate(
        is_closed_sort=Case(
            When(status='closed', then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        )
    ).order_by('is_closed_sort', 'task_id')

    navigation_tasks_qs = Task.objects.filter(_task_access_filter(user), parent__isnull=True).select_related(
        'section',
        'section__project',
    ).prefetch_related('tags').annotate(
        is_closed_sort=Case(
            When(status='closed', then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        )
    ).order_by('is_closed_sort', 'task_id')
    projects = _projects_for_user(user, navigation_tasks_qs)

    active_project = active_section.project if active_section else None
    if active_section:
        for project in projects:
            if project.id != active_section.project_id:
                continue
            active_project = project
            active_section = next((section for section in project.sections.all() if section.id == active_section.id), active_section)
            break

    if active_view is None:
        active_view = 'section' if active_section else 'projects'

    _decorate_directory_members(projects, current_user=user)

    shared_project_count = TaskProject.objects.filter(id__in=_task_shared_ids(user, TaskProject)).exclude(user=user).count()
    shared_group_count = _shared_sections_queryset(user).count()
    shared_task_count = _shared_tasks_queryset(user).filter(parent__isnull=True).count()

    if active_section:
        can_create_issue = active_section.project.user_id == user.id
    elif active_project:
        can_create_issue = active_project.user_id == user.id and active_project.sections.exists()
    else:
        can_create_issue = TaskSection.objects.filter(project__user=user).exists()

    return {
        'projects': projects,
        'active_project': active_project,
        'active_section': active_section,
        'active_view': active_view,
        'tasks': tasks_qs,
        'total_task_count': tasks_qs.count(),
        'total_group_count': len(_sections_for_projects(projects)),
        'tags': TaskTag.objects.filter(user=user).annotate(total_tasks=Count('tasks', filter=Q(tasks__user=user, tasks__parent__isnull=True))),
        'total_tag_count': TaskTag.objects.filter(user=user).count(),
        'shared_task_count': shared_task_count,
        'shared_group_count': shared_group_count,
        'shared_project_count': shared_project_count,
        'can_create_issue': can_create_issue,
    }


def _set_task_status(task, status):
    valid_statuses = {choice for choice, _label in Task.STATUS_CHOICES}
    if status not in valid_statuses:
        return False
    task.status = status
    task.save()
    return True


def _record_task_activity(task, actor, action, message='', kind='system', metadata=None):
    return TaskActivity.objects.create(
        task=task,
        actor=actor if getattr(actor, 'is_authenticated', False) else None,
        kind=kind,
        action=action,
        message=message,
        metadata=metadata or {},
    )


def _task_activity_snapshot(task):
    section = task.section
    project = section.project if section else None
    return {
        'title': task.title,
        'description': task.description,
        'status': task.status,
        'priority': task.priority,
        'section_id': task.section_id,
        'section_label': section.title if section else '',
        'project_id': project.id if project else None,
        'project_label': project.name if project else '',
        'parent_id': task.parent_id,
        'due_at': task.due_at,
        'time_spent_hours': task.time_spent_hours,
        'time_spent_minutes': task.time_spent_minutes,
        'completion_date': task.completion_date,
        'tags': set(task.tags.values_list('id', flat=True)),
        'tag_labels': list(task.tags.order_by('name').values_list('name', flat=True)),
    }


def _task_change_activities(task, before):
    status_labels = dict(Task.STATUS_CHOICES)
    priority_labels = dict(Task.PRIORITY_CHOICES)
    changed_fields = []
    detailed_changes = []

    def normalize_change_value(value):
        if hasattr(value, 'tzinfo'):
            return task._activity_datetime(value)
        if value in (None, ''):
            return '—'
        return str(value)

    def add_change(field_label, from_label, to_label):
        changed_fields.append(field_label)
        detailed_changes.append({
            'field': field_label,
            'from_label': normalize_change_value(from_label),
            'to_label': normalize_change_value(to_label),
        })

    if before['status'] != task.status:
        add_change('status', status_labels.get(before['status'], before['status']), task.get_status_display())
    if before['priority'] != task.priority:
        add_change('priorytet', priority_labels.get(before['priority'], before['priority']), task.get_priority_display())
    if before['title'] != task.title:
        add_change('tytuł', before['title'], task.title)
    if before['description'] != task.description:
        add_change('opis', before['description'], task.description)
    if before['project_id'] != (task.section.project_id if task.section_id else None):
        add_change('projekt', before['project_label'], task.section.project.name if task.section_id else '')
    if before['section_id'] != task.section_id:
        add_change('grupa', before['section_label'], task.section.title if task.section_id else '')
    if before['parent_id'] != task.parent_id:
        add_change('zadanie nadrzędne', before['parent_id'], task.parent_id)
    if before['due_at'] != task.due_at:
        add_change('termin wykonania', before['due_at'], task.due_at)
    if (
        before['time_spent_hours'] != task.time_spent_hours
        or before['time_spent_minutes'] != task.time_spent_minutes
    ):
        previous_time = f"{before['time_spent_hours'] or 0:02d}:{before['time_spent_minutes'] or 0:02d}"
        add_change('czas pracy', previous_time, task._activity_time_spent())
    if before['completion_date'] != task.completion_date:
        add_change('zamknięto', before['completion_date'], task._activity_datetime(task.completion_date))
    if before['tags'] != set(task.tags.values_list('id', flat=True)):
        add_change('tagi', ', '.join(before['tag_labels']), ', '.join(task.tags.order_by('name').values_list('name', flat=True)))

    changed_fields = list(dict.fromkeys(changed_fields))
    if changed_fields:
        return [{
            'action': 'updated',
            'message': 'zaktualizował zadanie',
            'metadata': {
                'fields': changed_fields,
                'changes': detailed_changes,
            },
        }]
    return []


def _is_ajax_request(request):
    return request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.POST.get('autosave') == '1'


def _form_error_messages(form):
    messages_list = []
    for field_name, errors in form.errors.items():
        field = form.fields.get(field_name)
        label = field.label if field else 'Formularz'
        for error in errors:
            messages_list.append(f'{label}: {error}')
    return messages_list


def _task_detail_payload(task):
    return {
        'title': task.title,
        'status': task.status,
        'status_label': task.get_status_display(),
        'priority': task.priority,
        'priority_label': task.get_priority_display(),
        'due_urgency': task.due_urgency,
        'completion_date': task._activity_datetime(task.completion_date) if task.completion_date else '',
        'time_spent_label': task.time_spent_label,
        'has_time_spent': task.has_time_spent,
    }


def _task_activity_html(activities):
    ordered_activities = sorted(activities, key=lambda activity: activity.id or 0, reverse=True)
    return ''.join(
        render_to_string('tasks/includes/task_activity_item.html', {'item': activity})
        for activity in ordered_activities
    )


@login_required
def tasks(request):
    return _tasks_page(request)


@login_required
def task_group(request, section_id):
    active_section = get_object_or_404(TaskSection.objects.select_related('project', 'project__user'), id=section_id)
    if not _user_can_access_section(request.user, active_section):
        raise PermissionDenied
    return _tasks_page(request, active_section=active_section)


def _tasks_page(request, active_section=None):
    project_form = TaskProjectForm(user=request.user)
    section_form = TaskSectionForm()
    tag_form = TaskTagForm()
    all_tasks_view = request.GET.get('view') == 'all-tasks' and not active_section
    my_tasks_view = request.GET.get('view') == 'my-tasks' and not active_section
    all_groups_view = request.GET.get('view') == 'all-groups' and not active_section
    tags_view = request.GET.get('view') == 'tags' and not active_section
    shared_tasks_view = request.GET.get('view') == 'shared-tasks' and not active_section
    shared_groups_view = request.GET.get('view') == 'shared-groups' and not active_section
    shared_projects_view = request.GET.get('view') == 'shared-projects' and not active_section
    active_project_id = request.POST.get('project_id') if request.method == 'POST' else request.GET.get('project')
    if (
        all_tasks_view
        or my_tasks_view
        or all_groups_view
        or tags_view
        or shared_tasks_view
        or shared_groups_view
        or shared_projects_view
    ):
        active_project_id = None
    if active_section:
        active_project_id = active_section.project_id
    active_project_for_form = None
    if active_project_id:
        active_project_for_form = TaskProject.objects.filter(id=active_project_id, user=request.user).first()
    task_modal_form = TaskModalForm(user=request.user, project=active_project_for_form, section=active_section)
    project_modal_open = False
    project_rename_modal_open = False
    project_rename_form = TaskProjectRenameForm(user=request.user)
    project_rename_project_id = ''
    section_create_modal_open = False
    section_create_project_id = active_project_id or ''
    section_rename_modal_open = False
    section_rename_form = TaskSectionRenameForm()
    section_rename_section_id = ''
    task_modal_open = False
    tag_modal_open = False
    tag_edit_mode = False
    tag_edit_tag_id = ''

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'create_project':
            project_form = TaskProjectForm(request.POST, user=request.user)
            if project_form.is_valid():
                with transaction.atomic():
                    project = project_form.save(commit=False)
                    project.user = request.user
                    project.save()
                    section_title = project_form.cleaned_data.get('section_title') or 'Nowa Grupa'
                    TaskSection.objects.create(
                        project=project,
                        title=section_title,
                        kind='custom',
                        order=0,
                    )
                messages.success(request, 'Projekt dodany.')
                return redirect(f"{reverse('tasks:tasks')}?project={project.id}")
            project_modal_open = True
            messages.error(request, 'Nie udało się dodać projektu.')

        if action == 'delete_project':
            project_ids = _posted_ids(request, 'project_ids', 'project_id')
            projects_to_delete = TaskProject.objects.filter(id__in=project_ids, user=request.user)
            if not projects_to_delete.exists():
                get_object_or_404(TaskProject, id=request.POST.get('project_id'), user=request.user)
            project_count = projects_to_delete.count()
            task_count = Task.objects.filter(section__project__in=projects_to_delete, user=request.user).count()
            with transaction.atomic():
                projects_to_delete.delete()
                Task._renumber_user_tasks(request.user)
            if project_count == 1 and task_count:
                messages.success(request, 'Projekt usunięty razem z zadaniami.')
            elif project_count == 1:
                messages.success(request, 'Projekt usunięty.')
            elif task_count:
                messages.success(request, f'Usunięto {project_count} projekty razem z zadaniami.')
            else:
                messages.success(request, f'Usunięto {project_count} projekty.')
            return redirect('tasks:tasks')

        if action in ('edit_project', 'rename_project'):
            project = get_object_or_404(TaskProject, id=request.POST.get('project_id'), user=request.user)
            project_rename_form = TaskProjectRenameForm(request.POST, instance=project, user=request.user)
            if project_rename_form.is_valid():
                project_rename_form.save()
                messages.success(request, 'Projekt zaktualizowany.')
                return redirect(f"{reverse('tasks:tasks')}?project={project.id}")
            project_rename_modal_open = True
            project_rename_project_id = project.id
            active_project_for_form = project
            messages.error(request, 'Nie udało się zaktualizować projektu.')

        if action == 'share_project':
            project = get_object_or_404(TaskProject, id=request.POST.get('project_id'), user=request.user)
            _share_task_directory_object(request, project)
            return redirect(_tasks_next_url(request))

        if action == 'unshare_project':
            project = get_object_or_404(TaskProject, id=request.POST.get('project_id'), user=request.user)
            _unshare_task_directory_object(request, project)
            return redirect(_tasks_next_url(request))

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

        if action == 'create_tag':
            tag_form = TaskTagForm(request.POST)
            if tag_form.is_valid():
                tag_name = tag_form.cleaned_data['name']
                if TaskTag.objects.filter(user=request.user, name__iexact=tag_name).exists():
                    tag_form.add_error('name', 'Taki tag już istnieje.')
                else:
                    tag = tag_form.save(commit=False)
                    tag.user = request.user
                    tag.save()
                    messages.success(request, 'Tag dodany.')
                    return redirect(f"{reverse('tasks:tasks')}?view=tags")
            tag_modal_open = True
            messages.error(request, 'Nie udało się dodać tagu.')

        if action == 'edit_tag':
            tag = get_object_or_404(TaskTag, id=request.POST.get('tag_id'), user=request.user)
            tag_form = TaskTagForm(request.POST, instance=tag)
            if tag_form.is_valid():
                tag_name = tag_form.cleaned_data['name']
                if TaskTag.objects.filter(user=request.user, name__iexact=tag_name).exclude(pk=tag.pk).exists():
                    tag_form.add_error('name', 'Taki tag już istnieje.')
                else:
                    tag_form.save()
                    messages.success(request, 'Tag zaktualizowany.')
                    return redirect(f"{reverse('tasks:tasks')}?view=tags")
            tag_modal_open = True
            tag_edit_mode = True
            tag_edit_tag_id = tag.id
            messages.error(request, 'Nie udało się zaktualizować tagu.')

        if action == 'delete_tag':
            tag_ids = _posted_ids(request, 'tag_ids', 'tag_id')
            tags_to_delete = TaskTag.objects.filter(id__in=tag_ids, user=request.user)
            if not tags_to_delete.exists():
                get_object_or_404(TaskTag, id=request.POST.get('tag_id'), user=request.user)
            tag_count = tags_to_delete.count()
            tags_to_delete.delete()
            if tag_count == 1:
                messages.success(request, 'Tag usunięty.')
            else:
                messages.success(request, f'Usunięto tagi ({tag_count}).')
            return redirect(f"{reverse('tasks:tasks')}?view=tags")

        if action in ('edit_section', 'rename_section'):
            section = get_object_or_404(TaskSection, id=request.POST.get('section_id'), project__user=request.user)
            section_rename_form = TaskSectionRenameForm(request.POST, instance=section)
            if section_rename_form.is_valid():
                section_rename_form.save()
                messages.success(request, 'Grupa zaktualizowana.')
                if all_groups_view:
                    return redirect(f"{reverse('tasks:tasks')}?view=all-groups")
                return redirect('tasks:task_group', section_id=section.id)
            section_rename_modal_open = True
            section_rename_section_id = section.id
            active_section = section
            active_project_for_form = section.project
            messages.error(request, 'Nie udało się zaktualizować grupy.')

        if action == 'share_section':
            section = get_object_or_404(TaskSection, id=request.POST.get('section_id'), project__user=request.user)
            _share_task_directory_object(request, section)
            return redirect(_tasks_next_url(request))

        if action == 'unshare_section':
            section = get_object_or_404(TaskSection, id=request.POST.get('section_id'), project__user=request.user)
            _unshare_task_directory_object(request, section)
            return redirect(_tasks_next_url(request))

        if action == 'delete_section':
            section_ids = _posted_ids(request, 'section_ids', 'section_id')
            sections_to_delete = TaskSection.objects.filter(id__in=section_ids, project__user=request.user)
            if not sections_to_delete.exists():
                get_object_or_404(TaskSection, id=request.POST.get('section_id'), project__user=request.user)
            section_count = sections_to_delete.count()
            project_id = sections_to_delete.values_list('project_id', flat=True).first()
            task_count = Task.objects.filter(section__in=sections_to_delete, user=request.user).count()
            with transaction.atomic():
                sections_to_delete.delete()
                Task._renumber_user_tasks(request.user)
            if section_count == 1 and task_count:
                messages.success(request, 'Grupa usunięta razem z zadaniami.')
            elif section_count == 1:
                messages.success(request, 'Grupa usunięta.')
            elif task_count:
                messages.success(request, f'Usunięto {section_count} grupy razem z zadaniami.')
            else:
                messages.success(request, f'Usunięto {section_count} grupy.')
            if all_groups_view:
                return redirect(f"{reverse('tasks:tasks')}?view=all-groups")
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
                task_modal_form.save_m2m()
                task.activities.filter(action='created').update(metadata={'title': task.title})
                messages.success(request, 'Zadanie dodane.')
                return redirect('tasks:task_group', section_id=task.section_id)
            task_modal_open = True
            messages.error(request, 'Nie udało się dodać zadania.')

    tasks_qs = Task.objects.filter(user=request.user, parent__isnull=True).select_related('section', 'section__project').prefetch_related('tags').annotate(
        is_closed_sort=Case(
            When(status='closed', then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        )
    ).order_by('is_closed_sort', 'task_id')

    navigation_tasks_qs = Task.objects.filter(_task_access_filter(request.user), parent__isnull=True).select_related(
        'section',
        'section__project',
    ).prefetch_related('tags').annotate(
        is_closed_sort=Case(
            When(status='closed', then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        )
    ).order_by('is_closed_sort', 'task_id')
    projects = _projects_for_user(request.user, navigation_tasks_qs)

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

    _decorate_directory_members(projects, current_user=request.user)

    orphan_tasks = tasks_qs.filter(section__isnull=True)
    orphan_status_groups = _decorate_status_groups(projects, orphan_tasks)
    all_status_groups = _status_groups_for_tasks(list(tasks_qs))
    all_sections = _sections_for_projects(projects)
    shared_projects = list(
        TaskProject.objects.filter(id__in=_task_shared_ids(request.user, TaskProject))
        .exclude(user=request.user)
        .select_related('user')
        .order_by('name')
    )
    shared_sections = list(
        _shared_sections_queryset(request.user)
        .select_related('project', 'project__user')
        .order_by('project__name', 'order', 'created_at')
    )
    shared_tasks_qs = _shared_tasks_queryset(request.user).filter(parent__isnull=True).select_related(
        'section',
        'section__project',
        'user',
    ).prefetch_related('tags').annotate(
        is_closed_sort=Case(
            When(status='closed', then=Value(1)),
            default=Value(0),
            output_field=IntegerField(),
        )
    ).order_by('is_closed_sort', 'created_at', 'id')
    shared_tasks = list(shared_tasks_qs)
    for shared_task in shared_tasks:
        shared_task.shared_view_url = reverse('tasks:view-shared-task', args=[shared_task.id])
    shared_status_groups = _status_groups_for_tasks(shared_tasks)
    if active_section and active_section.project.user_id != request.user.id:
        active_section_tasks = list(
            Task.objects.filter(
                _task_access_filter(request.user),
                section=active_section,
                parent__isnull=True,
            ).select_related('section', 'section__project').prefetch_related('tags').annotate(
                is_closed_sort=Case(
                    When(status='closed', then=Value(1)),
                    default=Value(0),
                    output_field=IntegerField(),
                )
            ).order_by('is_closed_sort', 'task_id')
        )
        for shared_task in active_section_tasks:
            shared_task.shared_view_url = reverse('tasks:view-shared-task', args=[shared_task.id])
        active_section.status_groups = _status_groups_for_tasks(active_section_tasks)
    _decorate_share_links(request, [*projects, *all_sections])
    tags = TaskTag.objects.filter(user=request.user).annotate(total_tasks=Count('tasks', filter=Q(tasks__user=request.user, tasks__parent__isnull=True)))
    if active_section:
        can_create_issue = active_section.project.user_id == request.user.id
    elif active_project:
        can_create_issue = active_project.user_id == request.user.id and active_project.sections.exists()
    else:
        can_create_issue = TaskSection.objects.filter(project__user=request.user).exists()

    if active_section:
        active_view = 'section'
    elif active_project:
        active_view = 'project'
    elif all_groups_view:
        active_view = 'all_groups'
    elif tags_view:
        active_view = 'tags'
    elif my_tasks_view:
        active_view = 'my_tasks'
    elif all_tasks_view:
        active_view = 'all_tasks'
    elif shared_tasks_view:
        active_view = 'shared_tasks'
    elif shared_groups_view:
        active_view = 'shared_groups'
    elif shared_projects_view:
        active_view = 'shared_projects'
    else:
        active_view = 'projects'

    context = {
        'projects': projects,
        'active_project': active_project,
        'active_section': active_section,
        'active_view': active_view,
        'visible_sections': [active_section] if active_section else [],
        'orphan_tasks': orphan_tasks,
        'orphan_status_groups': orphan_status_groups,
        'all_status_groups': all_status_groups,
        'shared_status_groups': shared_status_groups,
        'all_sections': all_sections,
        'shared_projects': shared_projects,
        'shared_sections': shared_sections,
        'shared_tasks': shared_tasks,
        'tasks': tasks_qs,
        'total_task_count': tasks_qs.count(),
        'total_group_count': len(all_sections),
        'tags': tags,
        'total_tag_count': tags.count(),
        'shared_task_count': len(shared_tasks),
        'shared_group_count': len(shared_sections),
        'shared_project_count': len(shared_projects),
        'share_user_options': _share_user_options(request.user),
        'tasks_return_path': request.get_full_path(),
        'project_form': project_form,
        'project_rename_form': project_rename_form,
        'project_rename_project_id': project_rename_project_id,
        'section_form': section_form,
        'tag_form': tag_form,
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
        'tag_modal_open': tag_modal_open,
        'tag_edit_mode': tag_edit_mode,
        'tag_edit_tag_id': tag_edit_tag_id,
        'can_create_issue': can_create_issue,
    }
    return render(request, 'tasks/tasks.html', context)


@login_required
@require_POST
def create_share_link(request):
    obj = _owned_share_object(
        request.user,
        (request.POST.get('object_type') or '').strip(),
        request.POST.get('object_id'),
    )
    link, created = SharedItemLink.objects.get_or_create(
        content_type=ContentType.objects.get_for_model(obj.__class__),
        object_id=obj.pk,
        created_by=request.user,
        is_active=True,
        defaults={'permission': 'view'},
    )
    return JsonResponse({
        'status': 'success',
        'created': created,
        'url': _share_link_url(request, link),
    })


@login_required
@require_POST
def revoke_share_link(request):
    obj = _owned_share_object(
        request.user,
        (request.POST.get('object_type') or '').strip(),
        request.POST.get('object_id'),
    )
    updated_count = SharedItemLink.objects.filter(
        content_type=ContentType.objects.get_for_model(obj.__class__),
        object_id=obj.pk,
        created_by=request.user,
        is_active=True,
    ).update(is_active=False, deactivated_at=timezone.now())

    return JsonResponse({
        'status': 'success',
        'revoked': bool(updated_count),
    })


@login_required
def accept_share_link(request, token):
    link = SharedItemLink.objects.select_related('content_type', 'created_by').filter(token=token).first()
    if not link:
        messages.error(request, 'Ten link udostępniania nie istnieje albo został przepisany niepoprawnie.')
        return redirect('tasks:tasks')
    if not link.is_active:
        messages.error(request, 'Ten link udostępniania został wyłączony.')
        return redirect('tasks:tasks')

    obj = link.content_object
    if not obj:
        messages.error(request, 'Ten link udostępniania nie prowadzi już do żadnego elementu.')
        return redirect('tasks:tasks')

    owner = _task_share_owner(obj)
    if owner == request.user:
        messages.info(request, 'To jest Twój element.')
    else:
        SharedItem.objects.update_or_create(
            content_type=link.content_type,
            object_id=link.object_id,
            shared_by=link.created_by,
            shared_with=request.user,
            defaults={'permission': link.permission},
        )
        messages.success(request, f'Dodano dostęp: {_task_share_type_label(obj).lower()} „{_task_share_label(obj)}”.')

    return redirect(_task_share_object_url(obj))


@login_required
@require_POST
def update_task_status(request, task_id):
    try:
        task = Task.objects.get(task_id=task_id, user=request.user)
        data = json.loads(request.body)
        status = data.get('status')
        previous_status = task.status

        if status:
            if not _set_task_status(task, status):
                return JsonResponse({'status': 'error', 'message': 'Nieprawidłowy status'}, status=400)
        else:
            is_completed = data.get('is_completed', False)
            _set_task_status(task, 'closed' if is_completed else 'reopened')

        if previous_status != task.status:
            status_labels = dict(Task.STATUS_CHOICES)
            _record_task_activity(
                task,
                request.user,
                'status_changed',
                'zmienił status',
                metadata={
                    'from_label': status_labels.get(previous_status, previous_status),
                    'to_label': task.get_status_display(),
                    'changes': [{
                        'field': 'status',
                        'from_label': status_labels.get(previous_status, previous_status),
                        'to_label': task.get_status_display(),
                    }],
                },
            )
        
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
        valid_statuses = {choice for choice, _label in Task.STATUS_CHOICES}
        if status not in valid_statuses:
            return JsonResponse({'status': 'error', 'message': 'Nieprawidłowy status'}, status=400)
        
        user = request.user
        tasks_to_update = Task.objects.filter(task_id__in=task_ids, user=user)
        updated_count = 0
        for task in tasks_to_update:
            _set_task_status(task, status)
            updated_count += 1
        
        return JsonResponse({
            'status': 'success', 
            'message': f'Zaktualizowano {updated_count} {"zadań" if updated_count != 1 else "zadanie"}',
            'updated_count': updated_count
        })
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Nieprawidłowy JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

def _task_detail_response(request, task_id=None, task_pk=None):
    task_queryset = Task.objects.select_related('section', 'section__project', 'section__project__user', 'parent').prefetch_related(
        Prefetch(
            'subtasks',
            queryset=Task.objects.select_related('section', 'section__project').prefetch_related('tags', 'attachments').order_by('task_id'),
        ),
        Prefetch(
            'activities',
            queryset=TaskActivity.objects.select_related('actor').order_by('created_at', 'id'),
        ),
    )
    if task_pk is not None:
        task = get_object_or_404(task_queryset.filter(_task_access_filter(request.user)), pk=task_pk)
    else:
        task = get_object_or_404(task_queryset, task_id=task_id, user=request.user)

    can_manage_task = task.user_id == request.user.id
    subtask_status_groups = _status_groups_for_tasks(list(task.subtasks.all()))
    can_add_attachments = can_manage_task and not task.parent_id
    form = TaskForm(instance=task, user=task.user)
    task_modal_form = SubTaskModalForm()
    task_modal_open = False
    _decorate_task_directory_members([task], current_user=request.user)
    _decorate_share_links(request, [task])

    if request.method == 'POST':
        is_ajax = _is_ajax_request(request)
        action = request.POST.get('action')
        if action == 'share_task':
            if not can_manage_task:
                raise PermissionDenied
            task_to_share = get_object_or_404(Task, id=request.POST.get('task_id'), user=request.user)
            _share_task_directory_object(request, task_to_share)
            return redirect(_tasks_next_url(request))
        if action == 'unshare_task':
            if not can_manage_task:
                raise PermissionDenied
            task_to_unshare = get_object_or_404(Task, id=request.POST.get('task_id'), user=request.user)
            _unshare_task_directory_object(request, task_to_unshare)
            return redirect(_tasks_next_url(request))
        if action == 'create_subtask_modal':
            if not can_manage_task:
                raise PermissionDenied
            task_modal_form = SubTaskModalForm(request.POST)
            if task_modal_form.is_valid():
                subtask = task_modal_form.save(commit=False)
                subtask.user = request.user
                subtask.parent = task
                subtask.section = task.section
                subtask.save()
                _record_task_activity(
                    task,
                    request.user,
                    'subtask_created',
                    'dodał podzadanie',
                    metadata={
                        'subtask_title': subtask.title,
                        'subtask_task_id': subtask.task_id,
                    },
                )
                messages.success(request, 'Podzadanie dodane.')
                return redirect('tasks:view-task', task_id=task.task_id)
            task_modal_open = True
            messages.error(request, 'Nie udało się dodać podzadania.')
        elif action == 'add_activity_comment':
            comment = (request.POST.get('activity_comment') or '').strip()
            if comment:
                _record_task_activity(
                    task,
                    request.user,
                    'commented',
                    comment,
                    kind='comment',
                )
                messages.success(request, 'Komentarz dodany.')
            else:
                messages.error(request, 'Wpisz treść komentarza.')
            if task.user_id == request.user.id:
                detail_route = 'tasks:view-subtask' if task.parent_id else 'tasks:view-task'
                return redirect(detail_route, task_id=task.task_id)
            return redirect('tasks:view-shared-task', task_pk=task.id)
        elif action == 'clear_time_spent':
            if not can_manage_task:
                raise PermissionDenied
            if task.has_time_spent:
                before = _task_activity_snapshot(task)
                task.time_spent_hours = None
                task.time_spent_minutes = None
                task.save(update_fields=['time_spent_hours', 'time_spent_minutes'])

                change_activities = _task_change_activities(task, before)
                recorded_activities = []
                for change in change_activities:
                    recorded_activities.append(
                        _record_task_activity(
                            task,
                            request.user,
                            change['action'],
                            change['message'],
                            metadata=change['metadata'],
                        )
                    )
                message = 'Czas pracy usunięty.'
                if is_ajax:
                    return JsonResponse({
                        'status': 'success',
                        'message': message,
                        'task': _task_detail_payload(task),
                        'activity_html': _task_activity_html(recorded_activities),
                    })
                messages.success(request, message)
            else:
                message = 'Brak czasu pracy do usunięcia.'
                if is_ajax:
                    return JsonResponse({
                        'status': 'success',
                        'message': message,
                        'task': _task_detail_payload(task),
                    })
                messages.info(request, message)
            detail_route = 'tasks:view-subtask' if task.parent_id else 'tasks:view-task'
            return redirect(detail_route, task_id=task.task_id)
        else:
            if not can_manage_task:
                raise PermissionDenied
            files = request.FILES.getlist('attachments') if can_add_attachments else []
            before = _task_activity_snapshot(task)
            form = TaskForm(request.POST, request.FILES, instance=task, user=task.user)
            if form.is_valid():
                form.save()
                recorded_activities = []

                # Handle staged attachment deletions
                deleted_attachments = request.POST.get('deleted_attachments', '')
                deleted_count = 0
                if deleted_attachments:
                    attachment_ids = [int(aid) for aid in deleted_attachments.split(',') if aid.isdigit()]
                    attachments_to_delete = TaskAttachment.objects.filter(id__in=attachment_ids, task=task)
                    deleted_count = attachments_to_delete.count()
                    attachments_to_delete.delete()

                # Handle new file attachments
                for file in files:
                    TaskAttachment.objects.create(
                        task=task,
                        file=file
                    )

                change_activities = _task_change_activities(task, before)
                for change in change_activities:
                    recorded_activities.append(
                        _record_task_activity(
                            task,
                            request.user,
                            change['action'],
                            change['message'],
                            metadata=change['metadata'],
                        )
                    )
                if files:
                    recorded_activities.append(
                        _record_task_activity(
                            task,
                            request.user,
                            'attachments_added',
                            'dodał załączniki',
                            metadata={'count': len(files)},
                        )
                    )
                if deleted_count:
                    recorded_activities.append(
                        _record_task_activity(
                            task,
                            request.user,
                            'attachments_deleted',
                            'usunął załączniki',
                            metadata={'count': deleted_count},
                        )
                    )

                if is_ajax:
                    task.refresh_from_db()
                    return JsonResponse({
                        'status': 'success',
                        'message': 'Zapisano automatycznie.',
                        'task': _task_detail_payload(task),
                        'changed_fields': [
                            field
                            for change in change_activities
                            for field in change.get('metadata', {}).get('fields', [])
                        ],
                        'attachments_added': len(files),
                        'attachments_deleted': deleted_count,
                        'activity_html': _task_activity_html(recorded_activities),
                    })

                messages.success(request, 'Zadanie zaktualizowane pomyślnie.')
                detail_route = 'tasks:view-subtask' if task.parent_id else 'tasks:view-task'
                return redirect(detail_route, task_id=task.task_id)
            else:
                if is_ajax:
                    error_messages = _form_error_messages(form)
                    return JsonResponse({
                        'status': 'error',
                        'message': error_messages[0] if error_messages else 'Nie udało się zapisać zmian.',
                        'errors': error_messages,
                    }, status=400)
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
    else:
        form = TaskForm(instance=task, user=task.user)

    if not can_manage_task:
        for field in form.fields.values():
            field.disabled = True

    context = {
        'form': form,
        'task_modal_form': task_modal_form,
        'task_modal_open': task_modal_open,
        'task': task,
        'can_manage_task': can_manage_task,
        'can_share_task': can_manage_task,
        'can_add_attachments': can_add_attachments,
        'activity_items': task.activities.order_by('-created_at', '-id'),
        'subtask_status_groups': subtask_status_groups,
        'share_user_options': _share_user_options(request.user),
        'tasks_return_path': request.get_full_path(),
        **_tasks_navigation_context(
            request.user,
            active_section=task.section,
            active_view='section' if task.section_id else 'all_tasks',
        ),
    }
    return render(request, 'tasks/view_task.html', context)


@login_required
def view_task(request, task_id):
    return _task_detail_response(request, task_id)

@login_required
def view_subtask(request, task_id):
    return _task_detail_response(request, task_id)

@login_required
def view_shared_task(request, task_pk):
    return _task_detail_response(request, task_pk=task_pk)
