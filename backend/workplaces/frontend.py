"""Workspace management contracts; selection never changes the active Workspace."""
from django.template.defaultfilters import date
from django.urls import reverse
from django.utils import timezone

from accounts.avatar import account_avatar
from core.frontend import form_payload
from .forms import MODULE_DETAILS
from .templatetags.workplace_avatar import workplace_avatar


def path(name, *args):
    return reverse('workplaces:' + name, args=args)


def person(user):
    return {'name': user.get_full_name() or user.username, 'email': user.email, 'avatar': account_avatar(user)}


def join_page(request, context):
    invitation = context['invitation']
    return {'type': 'account-join', 'title': 'Dołącz do Workspace', 'api_url': reverse('accounts-api'), 'data': {
        'name': invitation.workplace.name, 'role': invitation.get_role_display(),
        'error': context['join_error'], 'authenticated': request.user.is_authenticated,
        'urls': {key: reverse(key) for key in ('login', 'register', 'home', 'profile')},
    }}


def schema(form):
    if form is None:
        return None
    result = form_payload(form)
    for field in result['fields']:
        if field['name'] == 'enabled_modules':
            for choice in field['choices']:
                choice.update(MODULE_DETAILS.get(choice['value'], {}))
    if hasattr(form, 'automatic_avatar'):
        result['automatic_avatar'] = form.automatic_avatar
    return result


def form_page(request, context):
    modal = context['modal']
    return {'type': 'workspace-form', 'title': modal['title'], 'data': {
        'title': modal['title'], 'action': modal['action'], 'return_url': modal['return_url'],
        'form': schema(modal['form']),
    }}


def directory_page(request, context):
    selected = context.get('team_workplace')
    team = None
    if selected:
        manager, owner = context['can_manage_team'], context['is_team_owner']
        team = {
            'id': str(selected.pk), 'name': selected.name, 'code': selected.code, 'description': selected.description,
            'can_manage': manager, 'is_owner': owner, 'avatar': workplace_avatar(selected),
            'form': schema(context['avatar_edit_form']) if manager else None,
            'update_url': path('update', selected.pk) if manager else '',
            'add_url': path('team', selected.pk) if manager else '',
            'candidates_url': path('member-candidates', selected.pk) if manager else '',
            'add_form': schema(context['add_form']) if manager else None,
            'members': [{**person(member.user), 'id': str(member.pk), 'role': member.role,
                         'role_label': member.get_role_display(), 'self': member.user_id == request.user.pk,
                         'date': date(timezone.localtime(member.created_at), 'd.m.Y'),
                         'change_url': path('member-update', selected.pk, member.pk) if member.can_change else '',
                         'can_role': owner and member.can_change} for member in context['members']],
        }
        if manager:
            from .invitations import InviteLinkForm
            team['link_form'] = schema(InviteLinkForm())
            team['link_create_url'] = path('invite-link-create', selected.pk)
            team['invite_links'] = [{
                'id': str(link.pk), 'url': request.build_absolute_uri(path('join-link', link.token)),
                'role': link.get_role_display(),
                'uses': link.uses, 'limit': link.max_uses,
                'date': date(timezone.localtime(link.expires_at), 'd.m.Y H:i'),
                'revoke_url': path('invite-link-revoke', selected.pk, link.pk),
            } for link in selected.invite_links.filter(revoked_at__isnull=True, expires_at__gt=timezone.now()).order_by('-pk')]
    title = f'Ustawienia Workspace · {selected.name}' if context['workplace_edit_modal_open'] and selected else 'Workspace'
    return {'type': 'workspace-directory', 'title': title, 'data': {
        'base_url': path('workplaces'),
        'rows': [{'id': str(item.pk), 'name': item.name, 'code': item.code, 'description': item.description,
                  'avatar': workplace_avatar(item), 'members': item.team_member_count, 'role': item.viewer_role_label,
                  'can_manage': item.can_manage_team, 'active': item.pk == getattr(context['active_workplace'], 'pk', None),
                  'edit_url': item.edit_url, 'can_delete': item.can_delete, 'delete_url': item.delete_url,
                  'delete_disabled_reason': item.delete_disabled_reason,
                  'is_default': item.pk == request.user.default_workplace_id,
                  'default_url': path('set-default', item.pk),
                  'switch_url': path('switch', item.pk)} for item in context['workplaces']],
        'create_form': schema(context['form']), 'create_open': context['workplace_create_modal_open'],
        'edit_open': context['workplace_edit_modal_open'], 'tab': context['workplace_edit_tab'], 'team': team,
        'add_open': bool(context['add_form'].errors) if context.get('add_form') else False,
    }}
