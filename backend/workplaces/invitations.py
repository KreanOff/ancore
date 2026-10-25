"""Explicit, expiring Workspace invitations. Viewing a link never grants access."""
from datetime import timedelta
from urllib.parse import urlsplit

from django import forms
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST

from core.frontend import render
from .models import Workplace, WorkplaceInviteLink, WorkplaceInviteLinkUse, WorkplaceMembership
from .services import can_manage_team, set_active_workplace, enable_workspace_url_scope, scoped_workplace_app_path, workplace_management_url


def pending_join_url(request):
    path = request.session.get('workspace_join_url', '')
    # This value is set only by the invite landing page; fail closed on old sessions.
    from django.urls import resolve, Resolver404
    try:
        parsed = urlsplit(path)
        match = resolve(parsed.path)
        if not parsed.netloc and not parsed.scheme and match.view_name == 'workplaces:join-link':
            return parsed.path
    except (ValueError, Resolver404):
        pass
    return ''


class InviteLinkForm(forms.Form):
    role = forms.ChoiceField(label='Rola', choices=WorkplaceInviteLink._meta.get_field('role').choices)
    days = forms.IntegerField(label='Ważność (dni)', min_value=1, max_value=30, initial=7)
    max_uses = forms.IntegerField(label='Limit użyć', min_value=1, max_value=1000, initial=10)


@login_required
@require_POST
def create_link(request, workplace_id):
    with transaction.atomic():
        workplace = get_object_or_404(Workplace.objects.select_for_update(), pk=workplace_id)
        if not can_manage_team(request.user, workplace):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        if (request.POST.get('email_domain') or '').strip():
            return JsonResponse({'message': 'Ograniczenia domeny nie są obsługiwane. Utwórz link bez tego warunku.'}, status=400)
        form = InviteLinkForm(request.POST)
        if not form.is_valid():
            return JsonResponse({'message': 'Sprawdź ustawienia linku.', 'errors': form.errors}, status=400)
        WorkplaceInviteLink.objects.create(
            workplace=workplace, created_by=request.user, role=form.cleaned_data['role'],
            max_uses=form.cleaned_data['max_uses'],
            expires_at=timezone.now() + timedelta(days=form.cleaned_data['days']),
        )
    return redirect(workplace_management_url(workplace, 'links'))


@login_required
@require_POST
def revoke_link(request, workplace_id, link_id):
    with transaction.atomic():
        workplace = get_object_or_404(Workplace.objects.select_for_update(), pk=workplace_id)
        if not can_manage_team(request.user, workplace):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        link = get_object_or_404(WorkplaceInviteLink, pk=link_id, workplace=workplace)
        link.revoked_at = timezone.now()
        link.save(update_fields=['revoked_at'])
    return redirect(workplace_management_url(workplace, 'links'))


@never_cache
@require_http_methods(['GET', 'POST'])
def join(request, token):
    invitation = get_object_or_404(WorkplaceInviteLink.objects.select_related('workplace'), token=token)
    request.session['workspace_join_url'] = request.path_info
    error = ''
    if invitation.expires_at <= timezone.now() or invitation.revoked_at or invitation.uses >= invitation.max_uses:
        error = 'Zaproszenie jest już niedostępne. Poproś o nowe.'
    if request.method == 'POST' and request.user.is_authenticated and not error:
        with transaction.atomic():
            workplace = Workplace.objects.select_for_update().get(pk=invitation.workplace_id)
            invitation = WorkplaceInviteLink.objects.select_for_update().get(pk=invitation.pk)
            valid = invitation.expires_at > timezone.now() and not invitation.revoked_at and invitation.uses < invitation.max_uses
            if not valid:
                return render(request, 'workplaces/join.html', {
                    'invitation': invitation, 'join_error': 'Zaproszenie jest już niedostępne. Poproś o nowe.',
                }, status=400)
            # Never upgrade an existing member or a revoked member with an old invitation.
            membership = WorkplaceMembership.objects.filter(workplace=workplace, user=request.user).first()
            if membership is None and workplace.owner_id != request.user.pk:
                if invitation.redemptions.filter(user=request.user).exists():
                    from django.core.exceptions import PermissionDenied
                    raise PermissionDenied('Ten link został już wykorzystany przez to konto. Poproś o nowe zaproszenie.')
                WorkplaceMembership.objects.create(workplace=workplace, user=request.user, role=invitation.role)
                invitation.uses += 1
                invitation.save(update_fields=['uses'])
            elif membership and not membership.is_active:
                from django.core.exceptions import PermissionDenied
                raise PermissionDenied('Poproś administratora o ponowne nadanie dostępu.')
            WorkplaceInviteLinkUse.objects.get_or_create(link=invitation, user=request.user)
        set_active_workplace(request, workplace)
        enable_workspace_url_scope(request)
        request.session.pop('workspace_join_url', None)
        return redirect(scoped_workplace_app_path(workplace, 'for-you'))
    response = render(request, 'workplaces/join.html', {
        'invitation': invitation, 'join_error': error,
    }, status=400 if error and request.method == 'POST' else 200)
    response['Referrer-Policy'] = 'no-referrer'
    return response
