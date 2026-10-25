"""Explicit, expiring Workspace invitations. Viewing a link never grants access."""
from datetime import timedelta
from urllib.parse import urlsplit

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods, require_POST

from core.frontend import render
from .models import Workplace, WorkplaceInvitation, WorkplaceInviteLink, WorkplaceInviteLinkUse, WorkplaceMembership
from .services import can_manage_team, workplace_role, set_active_workplace, enable_workspace_url_scope, scoped_workplace_app_path, workplace_management_url


def pending_join_url(request):
    path = request.session.get('workspace_join_url', '')
    # This value is set only by the invite landing page; fail closed on old sessions.
    from django.urls import resolve, Resolver404
    try:
        parsed = urlsplit(path)
        match = resolve(parsed.path)
        if not parsed.netloc and not parsed.scheme and match.view_name in {'workplaces:join-link', 'workplaces:join-email'}:
            return parsed.path
    except (ValueError, Resolver404):
        pass
    return ''


def invitation_url(request, invitation):
    name = 'join-link' if isinstance(invitation, WorkplaceInviteLink) else 'join-email'
    return request.build_absolute_uri(reverse('workplaces:' + name, args=[invitation.token]))


def send_invitation(request, invitation):
    if not settings.EMAIL_HOST and settings.EMAIL_BACKEND == 'django.core.mail.backends.smtp.EmailBackend':
        return False
    try:
        sent = send_mail(
            f'Zaproszenie do Workspace: {invitation.workplace.name}',
            f'Zaproszono Cię do Workspace „{invitation.workplace.name}” w Ancore.\n'
            f'Rola: {invitation.get_role_display()}.\n'
            f'Zaproszenie jest ważne do {timezone.localtime(invitation.expires_at):%d.%m.%Y %H:%M}.\n\n'
            f'{invitation_url(request, invitation)}\n\n'
            'Zaloguj się lub utwórz konto z adresem, na który otrzymano zaproszenie, i potwierdź dołączenie.',
            settings.DEFAULT_FROM_EMAIL, [invitation.email or invitation.recipient.email], fail_silently=False,
        )
    except Exception:
        # Keep a usable invitation and allow an explicit retry; never expose SMTP credentials.
        return False
    if sent:
        invitation.email_sent_at = timezone.now()
        invitation.save(update_fields=['email_sent_at'])
    return bool(sent)


class InviteLinkForm(forms.Form):
    role = forms.ChoiceField(label='Rola', choices=WorkplaceInviteLink._meta.get_field('role').choices)
    days = forms.IntegerField(label='Ważność (dni)', min_value=1, max_value=30, initial=7)
    max_uses = forms.IntegerField(label='Limit użyć', min_value=1, max_value=1000, initial=10)
    email_domain = forms.CharField(label='Domena e-mail (opcjonalnie)', required=False, max_length=253)

    def clean_email_domain(self):
        domain = self.cleaned_data['email_domain'].strip().lower().lstrip('@')
        if domain:
            try:
                forms.EmailField().clean('invite@' + domain)
            except forms.ValidationError:
                raise forms.ValidationError('Wpisz poprawną domenę, np. firma.pl.')
        return domain


@login_required
@require_POST
def create_link(request, workplace_id):
    with transaction.atomic():
        workplace = get_object_or_404(Workplace.objects.select_for_update(), pk=workplace_id)
        if not can_manage_team(request.user, workplace):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        form = InviteLinkForm(request.POST)
        if not form.is_valid():
            return JsonResponse({'message': 'Sprawdź ustawienia linku.', 'errors': form.errors}, status=400)
        WorkplaceInviteLink.objects.create(
            workplace=workplace, created_by=request.user, role=form.cleaned_data['role'],
            email_domain=form.cleaned_data['email_domain'], max_uses=form.cleaned_data['max_uses'],
            expires_at=timezone.now() + timedelta(days=form.cleaned_data['days']),
        )
    return redirect(workplace_management_url(workplace, 'invitations'))


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
    return redirect(workplace_management_url(workplace, 'invitations'))


@login_required
@require_POST
def resend_email(request, workplace_id, invitation_id):
    workplace = get_object_or_404(Workplace, pk=workplace_id)
    role = workplace_role(request.user, workplace)
    invitation = get_object_or_404(WorkplaceInvitation, workplace=workplace, pk=invitation_id,
                                 status='pending', expires_at__gt=timezone.now())
    if role not in {'owner', 'admin'} or role == 'admin' and invitation.role == 'admin':
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied
    sent = send_invitation(request, invitation)
    messages.info(request, 'E-mail wysłany.' if sent else 'E-mail nie został wysłany. Sprawdź konfigurację poczty lub skopiuj link zaproszenia.')
    return redirect(workplace_management_url(workplace, 'invitations'))


@never_cache
@require_http_methods(['GET', 'POST'])
def join(request, token, email=False):
    model = WorkplaceInvitation if email else WorkplaceInviteLink
    invitation = get_object_or_404(model.objects.select_related('workplace'), token=token)
    request.session['workspace_join_url'] = request.path_info
    error = ''
    if invitation.expires_at <= timezone.now() or (email and invitation.status != 'pending') or (
        not email and (invitation.revoked_at or invitation.uses >= invitation.max_uses)
    ):
        error = 'Zaproszenie jest już niedostępne. Poproś o nowe.'
    if request.user.is_authenticated and not error:
        target_email = invitation.email or invitation.recipient.email if email else ''
        if email and request.user.email.casefold() != target_email.casefold():
            error = 'To zaproszenie jest przeznaczone dla innego adresu e-mail. Zaloguj się na właściwe konto.'
        elif not email and invitation.email_domain and request.user.email.rsplit('@', 1)[-1].casefold() != invitation.email_domain:
            error = 'Ten link wymaga konta z domeny ' + invitation.email_domain + '.'
    if request.method == 'POST' and request.user.is_authenticated and not error:
        with transaction.atomic():
            workplace = Workplace.objects.select_for_update().get(pk=invitation.workplace_id)
            invitation = model.objects.select_for_update().get(pk=invitation.pk)
            valid = invitation.expires_at > timezone.now() and (
                invitation.status == 'pending' if email else not invitation.revoked_at and invitation.uses < invitation.max_uses
            )
            if not valid:
                return render(request, 'workplaces/join.html', {
                    'invitation': invitation, 'join_error': 'Zaproszenie jest już niedostępne. Poproś o nowe.',
                }, status=400)
            # Never upgrade an existing member or a revoked member with an old invitation.
            membership = WorkplaceMembership.objects.filter(workplace=workplace, user=request.user).first()
            if membership is None and workplace.owner_id != request.user.pk:
                if not email and invitation.redemptions.filter(user=request.user).exists():
                    from django.core.exceptions import PermissionDenied
                    raise PermissionDenied('Ten link został już wykorzystany przez to konto. Poproś o nowe zaproszenie.')
                WorkplaceMembership.objects.create(workplace=workplace, user=request.user, role=invitation.role)
                if not email:
                    invitation.uses += 1
                    invitation.save(update_fields=['uses'])
            elif membership and not membership.is_active:
                from django.core.exceptions import PermissionDenied
                raise PermissionDenied('Poproś administratora o ponowne nadanie dostępu.')
            if not email:
                WorkplaceInviteLinkUse.objects.get_or_create(link=invitation, user=request.user)
            if email:
                invitation.status = 'accepted'
                invitation.recipient = request.user
                invitation.save(update_fields=['status', 'recipient'])
        set_active_workplace(request, workplace)
        enable_workspace_url_scope(request)
        request.session.pop('workspace_join_url', None)
        return redirect(scoped_workplace_app_path(workplace, 'for-you'))
    response = render(request, 'workplaces/join.html', {
        'invitation': invitation, 'join_error': error,
    }, status=400 if error and request.method == 'POST' else 200)
    response['Referrer-Policy'] = 'no-referrer'
    return response
