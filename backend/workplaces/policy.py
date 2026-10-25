"""Workspace-wide module and read-only rules, shared by HTML and delegated APIs."""
from django.core.exceptions import PermissionDenied
from django.http import Http404

from .services import workplace_role


MODULES = (
    ('spaces', 'Przestrzenie i zadania'), ('teams', 'Zespoły'),
    ('calendar', 'Kalendarz'), ('documents', 'Dysk'), ('office', 'Dokumenty'),
    ('resources', 'Zasoby'), ('dashboards', 'Pulpity'), ('filters', 'Filtry'),
)


def module_enabled(workplace, key):
    return not workplace or key not in workplace.disabled_modules


def read_only(request):
    return workplace_role(request.user, getattr(request, 'workplace', None)) == 'guest'


def module_for_request(request):
    return module_for_path(request.path_info)


def module_for_path(path):
    from urllib.parse import urlsplit
    parts = urlsplit(path).path.strip('/').split('/')
    if len(parts) >= 3 and parts[0] == 'workplaces':
        parts = parts[2:]
    key = parts[0] if parts else ''
    if not key:
        return 'dashboards'
    if key in dict(MODULES):
        return key
    if key == 'space':
        return 'spaces'
    return None


def check_access(request):
    workplace = getattr(request, 'workplace', None)
    module = module_for_request(request)
    if module and not module_enabled(workplace, module):
        raise Http404('Ten moduł jest wyłączony w Workspace.')
    if module and read_only(request):
        # Personal stars and reminders do not change shared data.
        name = request.resolver_match.url_name if request.resolver_match else ''
        personal = name in {'favorite', 'star', 'folder-star', 'reminder', 'reminder-create', 'reminder-delete'}
        if request.method not in {'GET', 'HEAD', 'OPTIONS'} and not personal:
            raise PermissionDenied('Gość ma dostęp tylko do odczytu.')
        if request.method in {'GET', 'HEAD'} and request.resolver_match:
            action = request.resolver_match.func.__name__
            if action in {'create', 'edit', 'new', 'upload', 'configuration', 'gadgets', 'gadget_edit',
                          'library_create', 'library_edit', 'folder_create', 'folder_edit', 'import_text',
                          'manage_create', 'manage_edit', 'members', 'team'}:
                raise PermissionDenied('Gość ma dostęp tylko do odczytu.')


def restrict_page(page):
    """Remove edit capabilities from page contracts; server checks remain authoritative."""
    denied = {'editable', 'manageable', 'deletable', 'query_editable', 'can_save', 'can_remove',
              'can_change', 'can_delete', 'can_manage', 'can_configure', 'can_edit', 'editing'}
    actions = {'create_url', 'create_item_url', 'sprint_create_url', 'backlog_create_url',
               'edit_url', 'delete_url', 'upload_url', 'folder_create_url', 'template_create_url',
               'configuration_url', 'member_url', 'bulk_plan_url', 'save_as_url', 'move_url',
               'rename_url', 'save_url', 'action_url', 'restore_url', 'trash_url'}
    def restrict(value):
        if isinstance(value, dict):
            for key in value:
                if key in denied:
                    value[key] = False
                elif key in actions:
                    value[key] = ''
                else:
                    restrict(value[key])
        elif isinstance(value, list):
            for item in value:
                restrict(item)
    restrict(page['data'])
