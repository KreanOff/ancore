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
            'invite_url': path('team', selected.pk) + '?view=invitations' if manager else '',
            'candidates_url': path('invitation-candidates', selected.pk) if manager else '',
            'invite_form': schema(context['invite_form']) if manager else None,
            'members': [{**person(member.user), 'id': str(member.pk), 'role': member.role,
                         'role_label': member.get_role_display(), 'self': member.user_id == request.user.pk,
                         'date': date(timezone.localtime(member.created_at), 'd.m.Y'),
                         'change_url': path('member-update', selected.pk, member.pk) if member.can_change else '',
                         'can_role': owner and member.can_change} for member in context['members']],
            'invitations': [{**(person(invitation.recipient) if invitation.recipient else {'name': invitation.email, 'email': invitation.email, 'avatar': {}}), 'id': str(invitation.pk), 'role': invitation.role,
                             'share_url': request.build_absolute_uri(path('join-email', invitation.token)),
                             'resend_url': path('invitation-resend', selected.pk, invitation.pk) if owner or invitation.role != 'admin' else '',
                             'email_sent': bool(invitation.email_sent_at),
                             'role_label': invitation.get_role_display(), 'date': date(timezone.localtime(invitation.expires_at), 'd.m.Y'),
                             'cancel_url': path('invitation-cancel', selected.pk, invitation.pk) if owner or invitation.role in {'member', 'guest'} else ''}
                            for invitation in context['team_invitations']],
        }
        if manager:
            from .invitations import InviteLinkForm
            team['link_form'] = schema(InviteLinkForm())
            team['link_create_url'] = path('invite-link-create', selected.pk)
            team['invite_links'] = [{
                'id': str(link.pk), 'url': request.build_absolute_uri(path('join-link', link.token)),
                'role': link.get_role_display(), 'domain': link.email_domain,
                'uses': link.uses, 'limit': link.max_uses,
                'date': date(timezone.localtime(link.expires_at), 'd.m.Y H:i'),
                'revoke_url': path('invite-link-revoke', selected.pk, link.pk),
            } for link in selected.invite_links.filter(revoked_at__isnull=True, expires_at__gt=timezone.now()).order_by('-pk')]
    invitation = context.get('response_invitation') if context['invitation_modal_open'] else None
    incoming = None
    if invitation:
        def invitation_url(item):
            return (path('workplaces') + f'?view=workspaces&invitation={item.pk}'
                    + (f'&workspace={selected.pk}' if selected else '')) if item else ''
        incoming = {'name': invitation.workplace.name,
                    'invited_by': invitation.invited_by.get_full_name() or invitation.invited_by.username if invitation.invited_by else 'System',
                    'role': invitation.get_role_display(), 'date': date(timezone.localtime(invitation.expires_at), 'd.m.Y'),
                    'action': path('invitation-response', invitation.pk), 'position': context['invitation_position'],
                    'count': len(context['pending_invitations']), 'previous': invitation_url(context['previous_invitation']),
                    'next': invitation_url(context['next_invitation'])}
    return {'type': 'workspace-directory', 'title': 'Workspace', 'data': {
        'base_url': path('workplaces'),
        'rows': [{'id': str(item.pk), 'name': item.name, 'code': item.code, 'description': item.description,
                  'avatar': workplace_avatar(item), 'members': item.team_member_count, 'role': item.viewer_role_label,
                  'can_manage': item.can_manage_team, 'active': item.pk == getattr(context['active_workplace'], 'pk', None),
                  'switch_url': path('switch', item.pk)} for item in context['workplaces']],
        'create_form': schema(context['form']), 'create_open': context['workplace_create_modal_open'],
        'edit_open': context['workplace_edit_modal_open'], 'tab': context['workplace_edit_tab'], 'team': team,
        'invite_open': bool(context['invite_form'].errors) if context.get('invite_form') else False,
        'incoming': incoming,
    }}
