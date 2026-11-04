"""Typed page data for React; business operations remain in their domain views."""
from copy import copy
from importlib import import_module
from urllib.parse import urlsplit

from django import forms
from django.core.exceptions import PermissionDenied
from django.http import Http404, JsonResponse, QueryDict
from django.shortcuts import render as django_render
from django.templatetags.static import static
from django.urls import resolve

from accounts.avatar import account_avatar
from workplaces.services import SCOPED_WORKPLACE_APPS, scoped_workplace_app_path
from .api import api_error, api_view, json_object


# Each screen has an explicit serializer. No HTML, model dumping or arbitrary view proxying.
SCREENS = {
    'accounts/login.html': ('accounts.frontend', 'login_page'),
    'accounts/register.html': ('accounts.frontend', 'register_page'),
    'accounts/register_workspace.html': ('accounts.frontend', 'register_workspace_page'),
    'accounts/select_workspace.html': ('accounts.frontend', 'select_workspace_page'),
    'workplaces/join.html': ('workplaces.frontend', 'join_page'),
    'accounts/profile.html': ('accounts.frontend', 'profile_page'),
    'workplaces/workplaces.html': ('workplaces.frontend', 'directory_page'),
    'planner/index.html': ('planner.frontend', 'calendar_page'),
    'dashboard/for_you.html': ('dashboard.frontend', 'for_you_page'),
    'dashboard/settings.html': ('dashboard.frontend', 'settings_page'),
    'spaces/index.html': ('spaces.frontend', 'directory_page'),
    'spaces/form_page.html': ('spaces.frontend', 'form_page'),
    'spaces/detail.html': ('spaces.frontend', 'detail_page'),
    'spaces/configuration.html': ('spaces.frontend', 'configuration_page'),
    'spaces/task_detail.html': ('spaces.frontend', 'task_page'),
    'spaces/teams.html': ('spaces.frontend', 'teams_page'),
    'spaces/team.html': ('spaces.frontend', 'team_page'),
    'spaces/tags.html': ('spaces.tag_frontend', 'tags_page'),
    'dashboard/filters/index.html': ('dashboard.filter_frontend', 'catalog_page'),
    'dashboard/filters/search.html': ('dashboard.filter_frontend', 'search_page'),
    'dashboard/pulpits/index.html': ('dashboard.pulpit_frontend', 'directory_page'),
    'dashboard/pulpits/detail.html': ('dashboard.pulpit_frontend', 'detail_page'),
    'dashboard/home.html': ('dashboard.pulpit_frontend', 'detail_page'),
    'dashboard/pulpits/gadgets.html': ('dashboard.pulpit_frontend', 'detail_page'),
    'dashboard/pulpits/edit.html': ('dashboard.pulpit_frontend', 'edit_page'),
    'documents/libraries.html': ('documents.frontend', 'directory_page'),
    'documents/library.html': ('documents.frontend', 'directory_page'),
    'documents/office/index.html': ('documents.frontend', 'directory_page'),
    'documents/form.html': ('documents.frontend', 'form_page'),
    'documents/preview.html': ('documents.frontend', 'form_page'),
    'documents/office/editor.html': ('documents.frontend', 'text_page'),
    'documents/office/suite.html': ('documents.frontend', 'suite_page'),
}
VIEWS = {
    'workplaces.invitations': {'create_link', 'revoke_link'},
    'accounts.views': {'profile'},
    'workplaces.views': {'workplaces', 'update_workplace', 'delete_workplace', 'switch_workplace', 'set_default_workplace', 'toggle_sidebar_favorite', 'reorder_sidebar_favorites'},
    'workplaces.team_views': {'team', 'member_candidates', 'member_update'},
    'planner.views': {'index', 'events_list', 'create_event', 'update_event', 'delete_event'},
    'dashboard.views': {'for_you', 'settings', 'home', 'global_search', 'notifications', 'notification_action'},
    'dashboard.filter_views': {'index', 'manage', 'search', 'lookup', 'edit', 'save_query', 'favorite', 'delete'},
    'dashboard.filter_sharing': {'team', 'candidates'},
    'dashboard.pulpit_views': {'index', 'search', 'manage', 'detail', 'default', 'gadgets', 'edit', 'access', 'delete', 'favorite', 'gadget_edit', 'gadget_delete', 'gadget_quick_add', 'arrange'},
    'dashboard.pulpit_sharing': {'team', 'candidates'},
    'spaces.views': {'index', 'search', 'manage', 'detail', 'configuration', 'edit', 'avatar_edit', 'favorite', 'members', 'remove_member', 'item_edit', 'item_action', 'backlog_plan', 'sprint_create', 'sprint_plan', 'sprint_action'},
    'spaces.task_views': {'detail', 'members'},
    'spaces.task_team': {'team', 'candidates'},
    'spaces.space_team': {'team', 'candidates'},
    'spaces.dashboard': {'save_layout'},
    'spaces.timeline': {'update_dates'},
    'spaces.teams': {'index', 'detail', 'edit', 'delete', 'members', 'remove_member'},
    'documents.views': {'library', 'library_create', 'library_edit', 'library_delete', 'upload', 'folder_create', 'folder_edit', 'folder_delete', 'folder_star', 'detail', 'preview', 'star', 'trash', 'restore'},
    'documents.editor_views': {'index', 'upload', 'edit', 'preview', 'import_text', 'action'},
    'documents.move_views': {'move'},
    'documents.suite_views': {'create', 'editor', 'rename', 'save_office', 'state', 'convert', 'upgrade_text'},
    'documents.office_extras': {'from_template', 'template_toggle'},
}
# These existing operations validate their structured JSON body themselves.
JSON_BODY_VIEWS = {('dashboard.pulpit_views', 'gadget_quick_add'), ('dashboard.pulpit_views', 'arrange'),
                   ('spaces.dashboard', 'save_layout')}


def api_url(request):
    return scoped_workplace_app_path(request.workplace, 'api', 'v1/page/') if request.workplace else '/api/v1/page/'


def render(request, template_name, context=None, *args, **kwargs):
    registration = SCREENS.get(template_name)
    if not registration:
        if getattr(request, '_react_api', False):
            return api_error('Ten ekran nie udostępnia jeszcze danych React.', 501)
        return django_render(request, template_name, context, *args, **kwargs)
    context = dict(context or {})
    serializer = getattr(import_module(registration[0]), registration[1])
    page = serializer(request, context)
    from workplaces.policy import read_only, restrict_page
    page['read_only'] = read_only(request) and not page['type'].startswith(('account-', 'workspace-'))
    if page['read_only']:
        restrict_page(page)
    page.update(url=request.get_full_path())
    page.setdefault('api_url', api_url(request))
    if getattr(request, '_react_api', False):
        from .shell import page_styles
        page['styles'] = page_styles(page)
        if getattr(request, '_react_navigation', False):
            from .shell import navigation_response
            return navigation_response(request, page, context, status=kwargs.get('status', 200))
        return JsonResponse(page, status=kwargs.get('status', 200))
    context['frontend_bootstrap'] = page
    return django_render(request, template_name, context, *args, **kwargs)


def form_payload(form):
    """Expose only the fields and relationship choices authorized by the original form."""
    fields = []
    for bound in form:
        field, widget = bound.field, bound.field.widget
        value = widget.format_value(bound.value())
        info = {
            'name': bound.html_name, 'field_name': bound.name, 'id': bound.id_for_label or bound.auto_id, 'label': str(field.label or ''),
            'required': bool(field.required and form.use_required_attribute and widget.use_required_attribute(bound.initial)), 'disabled': field.disabled, 'value': value,
            'hidden': bound.is_hidden, 'checked': bool(bound.value()) if isinstance(widget, forms.CheckboxInput) else False,
            'help_text': str(field.help_text), 'errors': list(bound.errors),
            'type': 'textarea' if isinstance(widget, forms.Textarea) else getattr(widget, 'input_type', 'text'),
            'attrs': {
                key: str(val) for key, val in {**widget.attrs, **field.widget_attrs(widget)}.items()
                if (key in {'placeholder', 'min', 'max', 'step', 'rows', 'accept', 'title', 'pattern', 'readonly'}
                    or key.startswith('data-ancore-custom-select-')) and (key != 'readonly' or val)
            },
        }
        if getattr(field, 'max_length', None):
            info['attrs']['maxlength'] = str(field.max_length)
        if getattr(widget, 'emoji_picker', False):
            from .emoji import emoji_picker_config
            info['type'] = 'emoji'
            info['emoji_picker'] = emoji_picker_config(bound.value() or 'layout-dashboard')
        if isinstance(field, (forms.ChoiceField, forms.ModelChoiceField)):
            info['type'] = 'checkboxes' if isinstance(widget, forms.CheckboxSelectMultiple) else 'select'
            info['multiple'] = isinstance(field, (forms.MultipleChoiceField, forms.ModelMultipleChoiceField))
            choices = []
            for option_value, label in field.choices:
                if isinstance(label, (list, tuple)):
                    choices.extend({'value': str(key), 'label': str(text), 'group': str(option_value)} for key, text in label)
                    continue
                choice = {'value': str(option_value), 'label': str(label)}
                if hasattr(widget, 'option_visual'):
                    visual = widget.option_visual(option_value)
                    if visual.get('icon'):
                        choice['icon'] = visual['icon']
                    if visual.get('context', {}).get('type_color'):
                        choice['type_color'] = visual['context']['type_color']
                    if visual.get('preserve_only'):
                        choice['preserve_only'] = True
                    if visual.get('context', {}).get('photo_url'):
                        choice['photo_url'] = visual['context']['photo_url']
                    if visual.get('context', {}).get('space'):
                        from spaces.avatars import space_avatar
                        choice['space_avatar'] = space_avatar(visual['context']['space'])
                    if visual.get('context', {}).get('avatar'):
                        choice['avatar'] = visual['context']['avatar']
                    if visual.get('context', {}).get('category'):
                        choice['status_category'] = visual['context']['category']
                        if visual['context'].get('color'):
                            choice['status_color'] = visual['context']['color']
                    if visual.get('context', {}).get('priority'):
                        choice['priority'] = visual['context']['priority']
                elif hasattr(widget, 'create_option'):
                    option = widget.create_option(bound.html_name, option_value, label, False, len(choices))
                    if option['attrs'].get('data-ancore-option-icon'):
                        choice['icon'] = option['attrs']['data-ancore-option-icon']
                instance = getattr(option_value, 'instance', None)
                if instance is not None and instance._meta.label_lower == 'accounts.user':
                    choice['avatar'] = account_avatar(instance)
                choices.append(choice)
            info['choices'] = choices
        if isinstance(widget, forms.FileInput):
            info['multiple'] = bool(widget.attrs.get('multiple'))
        fields.append(info)
    result = {'fields': fields, 'errors': list(form.non_field_errors()), 'bound': form.is_bound,
              'submit_label': getattr(form, 'submit_label', 'Zapisz'), 'compact': bool(getattr(form, 'compact', False))}
    if getattr(form, 'template_options', None):
        result['templates'] = [{**option, 'image': static(f'img/space-templates/{option["key"]}.svg')} for option in form.template_options]
    if getattr(form, 'avatar_options', None):
        result['avatars'] = form.avatar_options
        result['current_avatar'] = form.current_avatar
        if getattr(form, 'automatic_avatar', None):
            result['automatic_avatar'] = form.automatic_avatar
        if getattr(form, 'inline_avatar', False):
            result['inline_avatar'] = True
    if getattr(form, 'planning_summary', None):
        result['planning_summary'] = form.planning_summary
        result['sprint_name'] = form.sprint_name
    return result


def pagination_payload(request, page, base=None):
    if page is None:
        return None
    def url(number):
        params = request.GET.copy()
        params['page'] = number
        return (base or request.path) + '?' + params.urlencode()
    return {'page': page.number, 'count': page.paginator.count, 'start': page.start_index(), 'end': page.end_index(),
            'previous': url(page.previous_page_number()) if page.has_previous() else '',
            'next': url(page.next_page_number()) if page.has_next() else '',
            'pages': [{'label': str(number), 'url': '' if number == page.paginator.ELLIPSIS else url(number),
                       'current': number == page.number} for number in page.paginator.get_elided_page_range(page.number, on_each_side=1, on_ends=1)]}


@api_view(['GET', 'POST'])
def page_api(request):
    return dispatch(request)


def target_request(request):
    """Resolve only registered domain views inside the current Workspace."""
    target = request.GET.get('url', '')
    try:
        parsed = urlsplit(target)
    except ValueError:
        raise ValueError('Nieprawidłowy adres ekranu.')
    if not target.startswith('/') or target.startswith('//') or parsed.netloc or parsed.scheme or '\\' in target:
        raise ValueError('Nieprawidłowy adres ekranu.')
    match = resolve(parsed.path)
    module, name = match.func.__module__, match.func.__name__
    if name not in VIEWS.get(module, set()) and not (getattr(request, '_react_navigation', False) and module == 'resources.views' and name in {'index', 'edit', 'overview'}):
        raise Http404
    segments = parsed.path.strip('/').split('/')
    if len(segments) >= 3 and segments[0] == 'workplaces' and segments[2] in SCOPED_WORKPLACE_APPS:
        if not request.workplace or segments[1] not in {request.workplace.slug, request.workplace.legacy_slug}:
            raise PermissionDenied
    delegated = copy(request)
    delegated.META = request.META.copy()
    delegated.path = delegated.path_info = parsed.path
    delegated.META['PATH_INFO'] = parsed.path
    delegated.META['QUERY_STRING'] = parsed.query
    delegated.GET = QueryDict(parsed.query)
    delegated.resolver_match = match
    delegated._react_api = True
    for key in ('HTTP_X_WORK_MODAL', 'HTTP_X_RESOURCE_MODAL', 'HTTP_X_REQUESTED_WITH',
                'HTTP_X_FILTER_MODAL', 'HTTP_X_FILTER_NAVIGATION', 'HTTP_X_PULPIT_MODAL', 'HTTP_X_PULPIT_NAVIGATION',
                'HTTP_X_DOCUMENT_MODAL', 'HTTP_X_DOCUMENT_MOVE', 'HTTP_X_OFFICE_EDITOR'):
        delegated.META.pop(key, None)
    delegated.__dict__.pop('headers', None)
    return delegated, match


def dispatch(request):
    try:
        delegated, match = target_request(request)
    except ValueError as error:
        return api_error(str(error), 400)
    module, name = match.func.__module__, match.func.__name__
    from workplaces.policy import check_access, module_for_request
    if request.workplace is None and module_for_request(delegated):
        from django.urls import reverse
        return JsonResponse({'redirect': reverse('register_workspace')})
    check_access(delegated)
    if request.method == 'POST' and request.content_type == 'application/json' and (module, name) not in JSON_BODY_VIEWS:
        try:
            values = json_object(request)
        except ValueError as error:
            return api_error(str(error), 400)
        data = QueryDict(mutable=True)
        for key, value in values.items():
            data[key] = str(value)
        delegated.POST = data
    response = match.func(delegated, *match.args, **match.kwargs)
    for key in ('CSRF_COOKIE', 'CSRF_COOKIE_NEEDS_UPDATE'):
        if key in delegated.META:
            request.META[key] = delegated.META[key]
    if response.status_code in {301, 302, 303, 307, 308}:
        return JsonResponse({'redirect': response['Location']})
    if response.get('Content-Type', '').startswith('application/json'):
        return response
    return api_error('Ta operacja nie jest obsługiwana.', response.status_code if response.status_code >= 400 else 501)


@api_view(['GET'])
def navigation_api(request):
    request._react_navigation = True
    return dispatch(request)


@api_view(['GET'])
def shell_api(request):
    from .shell import shell_payload
    request._react_navigation = True
    try:
        delegated, _ = target_request(request)
    except ValueError as error:
        return api_error(str(error), 400)
    data = shell_payload(delegated)
    # Refreshing stars/Favorites must not replace an editor's context or a page draft.
    return JsonResponse({key: data[key] for key in ('account_id', 'workplace_id', 'collections', 'favorites')})
