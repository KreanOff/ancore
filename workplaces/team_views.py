"""Workspace membership and invitations, authorized independently of active space."""
import uuid

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST, require_http_methods
from django import forms

from .models import Workplace, WorkplaceInvitation, WorkplaceMembership
from .services import can_manage_team, workplace_role, workplaces_for_user, set_active_workplace, scoped_workplace_app_path, workplace_management_url


class InvitationForm(forms.Form):
    email = forms.EmailField(label='Adres e-mail konta Ancore', widget=forms.EmailInput(attrs={'class': 'form-input', 'autocomplete': 'email'}))
    role = forms.ChoiceField(label='Rola', choices=[('member', 'Członek'), ('admin', 'Administrator')], widget=forms.Select(attrs={'class': 'form-select'}))

    def __init__(self, *args, workplace, actor, **kwargs):
        super().__init__(*args, **kwargs)
        self.workplace = workplace
        if workplace.owner_id != actor.pk:
            self.fields['role'].choices = [('member', 'Członek')]

    def clean_email(self):
        email = self.cleaned_data['email'].strip()
        recipient = get_user_model().objects.filter(email__iexact=email, is_active=True).first()
        if not recipient:
            raise forms.ValidationError('Nie znaleziono aktywnego konta Ancore z tym adresem. Poproś tę osobę o rejestrację.')
        if recipient.pk == self.workplace.owner_id or self.workplace.memberships.filter(user=recipient, is_active=True).exists():
            raise forms.ValidationError('Ta osoba jest już członkiem Workspace.')
        if self.workplace.invitations.filter(recipient=recipient, status='pending', expires_at__gt=timezone.now()).exists():
            raise forms.ValidationError('Ta osoba ma już oczekujące zaproszenie.')
        self.recipient = recipient
        return email


@login_required
@require_http_methods(['GET', 'POST'])
def team(request, workplace_id):
    workplace = get_object_or_404(workplaces_for_user(request.user), pk=workplace_id)
    if request.method == 'GET':
        return redirect(workplace_management_url(workplace, request.GET.get('view')))
    form = InvitationForm(workplace=workplace, actor=request.user)
    if request.method == 'POST':
        with transaction.atomic():
            workplace = get_object_or_404(Workplace.objects.select_for_update(), pk=workplace_id)
            if not can_manage_team(request.user, workplace):
                raise PermissionDenied
            form = InvitationForm(request.POST, workplace=workplace, actor=request.user)
            if form.is_valid():
                workplace.invitations.filter(recipient=form.recipient, status='pending').update(status='revoked')
                WorkplaceInvitation.objects.create(workplace=workplace, recipient=form.recipient, invited_by=request.user, role=form.cleaned_data['role'])
                messages.success(request, 'Zaproszenie dodane. Osoba zobaczy je w powiadomieniach i na ekranie Workspace.')
                return redirect(workplace_management_url(workplace, 'invitations'))
    from .views import render_workplaces
    return render_workplaces(request, team_workplace=workplace, invite_form=form)


def team_context(request, workplace, invite_form=None):
    """Read one accessible team's details for the shared management screen."""
    members = list(workplace.memberships.filter(is_active=True).select_related('user').order_by('role', 'user__email'))
    members.sort(key=lambda member: (member.user_id != workplace.owner_id, member.role != 'admin', member.user.email))
    role = workplace_role(request.user, workplace)
    for member in members:
        member.can_change = member.user_id != workplace.owner_id and (
            role == 'owner' or (role == 'admin' and member.role == 'member')
        )
    return {
        'team_workplace': workplace, 'members': members,
        'invite_form': invite_form if invite_form is not None else InvitationForm(workplace=workplace, actor=request.user),
        'show_invitations': request.GET.get('view') == 'invitations' and role in {'owner', 'admin'},
        'can_manage_team': role in {'owner', 'admin'}, 'is_team_owner': role == 'owner',
        'team_invitations': workplace.invitations.filter(status='pending', expires_at__gt=timezone.now()).select_related('recipient') if role in {'owner', 'admin'} else [],
    }


@login_required
@require_POST
def invitation_response(request, invitation_id):
    invitation = get_object_or_404(WorkplaceInvitation, pk=invitation_id, recipient=request.user)
    with transaction.atomic():
        workplace = get_object_or_404(Workplace.objects.select_for_update(), pk=invitation.workplace_id)
        invitation = get_object_or_404(WorkplaceInvitation.objects.select_for_update(), pk=invitation.pk, recipient=request.user, status='pending', expires_at__gt=timezone.now())
        action = request.POST.get('action')
        if action not in {'accept', 'decline'}:
            raise PermissionDenied
        if action == 'accept':
            member, created = WorkplaceMembership.objects.get_or_create(workplace=workplace, user=request.user, defaults={'role': invitation.role})
            if not created and not member.is_active:
                member.role, member.is_active = invitation.role, True
                member.save(update_fields=['role', 'is_active'])
            invitation.status = 'accepted'
        else:
            invitation.status = 'declined'
        invitation.save(update_fields=['status'])
    if action == 'accept':
        set_active_workplace(request, workplace)
        messages.success(request, f'Dołączono do {workplace.name}.')
        return redirect(scoped_workplace_app_path(workplace, 'tasks'))
    messages.success(request, 'Zaproszenie odrzucone.')
    return redirect('workplaces:workplaces')


@login_required
@require_POST
def member_update(request, workplace_id, member_id):
    with transaction.atomic():
        workplace = get_object_or_404(Workplace.objects.select_for_update(), pk=workplace_id)
        role = workplace_role(request.user, workplace)
        member = get_object_or_404(WorkplaceMembership, pk=member_id, workplace=workplace)
        if member.user_id == workplace.owner_id or role not in {'owner', 'admin'} or (role == 'admin' and member.role != 'member'):
            raise PermissionDenied
        action = request.POST.get('action')
        if action == 'remove':
            # Pending invitations must not restore access after removal.
            workplace.invitations.filter(recipient=member.user, status='pending').update(status='revoked')
            member.delete()
            # End existing shared editor sessions too: a coauthor's old callback
            # URL could otherwise keep a removed user's editing session alive.
            from documents.models import Document, WorkspaceDocument
            for model in (Document, WorkspaceDocument):
                model.objects.filter(owner=workplace.owner, workplace=workplace).update(office_key=uuid.uuid4())
            messages.success(request, 'Dostęp odebrany. Dane zespołu pozostały w Workspace.')
        elif action == 'role' and role == 'owner' and request.POST.get('role') in {'admin', 'member'}:
            member.role = request.POST['role']
            member.save(update_fields=['role'])
            messages.success(request, 'Rola zmieniona.')
        else:
            raise PermissionDenied
    return redirect(workplace_management_url(workplace))


@login_required
@require_POST
def invitation_cancel(request, workplace_id, invitation_id):
    with transaction.atomic():
        workplace = get_object_or_404(Workplace.objects.select_for_update(), pk=workplace_id)
        role = workplace_role(request.user, workplace)
        invitation = get_object_or_404(WorkplaceInvitation, pk=invitation_id, workplace=workplace, status='pending')
        if role not in {'owner', 'admin'} or (role == 'admin' and invitation.role != 'member'):
            raise PermissionDenied
        invitation.status = 'revoked'
        invitation.save(update_fields=['status'])
    messages.success(request, 'Zaproszenie anulowane.')
    return redirect(workplace_management_url(workplace, 'invitations'))
