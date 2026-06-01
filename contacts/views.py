from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import CompanyForm, ContactForm, ShareItemForm
from .models import Company, CompanyMembership, Contact, ContactActivity, SharedItem, UserContact


def _content_type_for(model):
    return ContentType.objects.get_for_model(model)


def _shared_object_ids(user, model, permission=None):
    filters = {
        'shared_with': user,
        'content_type': _content_type_for(model),
    }
    if permission:
        filters['permission'] = permission
    return SharedItem.objects.filter(**filters).values('object_id')


def _has_edit_access(user, obj):
    owner = getattr(obj, 'user', None) or getattr(obj, 'owner', None)
    if owner == user:
        return True
    return SharedItem.objects.filter(
        shared_with=user,
        content_type=_content_type_for(obj.__class__),
        object_id=obj.pk,
        permission='edit',
    ).exists()


def _visible_contacts_queryset(user):
    return Contact.objects.filter(
        Q(user=user) | Q(pk__in=_shared_object_ids(user, Contact))
    ).distinct()


def _contacts_queryset(user):
    return _visible_contacts_queryset(user).annotate(
        activity_count=Count('activities')
    ).order_by('first_name', 'last_name', 'company')


def _visible_companies_queryset(user):
    return Company.objects.filter(
        Q(owner=user) | Q(pk__in=_shared_object_ids(user, Company))
    ).distinct().order_by('name')


def _contacts_navigation_context(user, active_status='all'):
    contacts_qs = _contacts_queryset(user)
    status_counts = {
        row['status']: row['count']
        for row in _visible_contacts_queryset(user).values('status').annotate(count=Count('id'))
    }
    status_rows = [
        {
            'value': value,
            'label': label,
            'count': status_counts.get(value, 0),
        }
        for value, label in Contact.STATUS_CHOICES
    ]
    return {
        'contacts_nav': contacts_qs[:30],
        'total_contact_count': contacts_qs.count(),
        'total_company_count': _visible_companies_queryset(user).count(),
        'total_user_contact_count': UserContact.objects.filter(owner=user).count(),
        'shared_received_count': SharedItem.objects.filter(shared_with=user).count(),
        'active_contact_status': active_status,
        'contact_status_rows': status_rows,
        'contact_status_choices': Contact.STATUS_CHOICES,
    }


def _record_contact_activity(contact, actor, action, message='', kind='system', metadata=None):
    return ContactActivity.objects.create(
        contact=contact,
        actor=actor if getattr(actor, 'is_authenticated', False) else None,
        action=action,
        message=message,
        kind=kind,
        metadata=metadata or {},
    )


def _contact_snapshot(contact):
    return {
        'first_name': contact.first_name,
        'last_name': contact.last_name,
        'company': contact.company,
        'role': contact.role,
        'email': contact.email,
        'phone': contact.phone,
        'source': contact.source,
        'status': contact.status,
        'last_contacted_at': contact.last_contacted_at,
        'notes': contact.notes,
    }


def _contact_change_activities(contact, before):
    labels = {
        'first_name': 'imię',
        'last_name': 'nazwisko',
        'company': 'firma',
        'role': 'stanowisko',
        'email': 'email',
        'phone': 'telefon',
        'source': 'źródło',
        'status': 'status',
        'last_contacted_at': 'ostatni kontakt',
        'notes': 'notatki',
    }
    status_labels = dict(Contact.STATUS_CHOICES)
    changes = []

    def format_value(field, value):
        if field == 'status':
            return status_labels.get(value, value) or '—'
        if field == 'last_contacted_at' and value:
            return value.strftime('%d.%m.%Y %H:%M')
        if value in (None, ''):
            return '—'
        return str(value)

    for field, previous_value in before.items():
        current_value = getattr(contact, field)
        if previous_value == current_value:
            continue
        changes.append({
            'field': labels[field],
            'from_label': format_value(field, previous_value),
            'to_label': format_value(field, current_value),
        })

    if not changes:
        return []
    return [{
        'action': 'updated',
        'message': 'zaktualizował kontakt',
        'metadata': {
            'fields': [change['field'] for change in changes],
            'changes': changes,
        },
    }]


@login_required
def contacts(request):
    query = (request.GET.get('q') or '').strip()
    status = (request.GET.get('status') or 'all').strip()
    contacts_qs = _contacts_queryset(request.user)

    if query:
        contacts_qs = contacts_qs.filter(
            Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(company__icontains=query)
            | Q(company_record__name__icontains=query)
            | Q(email__icontains=query)
            | Q(phone__icontains=query)
        )
    if status != 'all':
        contacts_qs = contacts_qs.filter(status=status)

    context = {
        'contacts': contacts_qs,
        'query': query,
        'status': status,
        **_contacts_navigation_context(request.user, active_status=status),
    }
    return render(request, 'contacts/contacts.html', context)


@login_required
def create_contact(request):
    form = ContactForm(request.POST or None, user=request.user)
    if request.method == 'POST':
        if form.is_valid():
            contact = form.save(commit=False)
            contact.user = request.user
            contact.save()
            _record_contact_activity(
                contact,
                request.user,
                'created',
                'utworzył kontakt',
                metadata={'title': contact.display_name},
            )
            messages.success(request, 'Kontakt dodany.')
            return redirect('contacts:view-contact', contact_id=contact.pk)
        messages.error(request, 'Nie udało się dodać kontaktu.')

    context = {
        'form': form,
        'is_create': True,
        **_contacts_navigation_context(request.user),
    }
    return render(request, 'contacts/view_contact.html', context)


@login_required
def view_contact(request, contact_id):
    contact = get_object_or_404(
        _visible_contacts_queryset(request.user).prefetch_related('activities__actor'),
        pk=contact_id,
    )
    can_edit_contact = _has_edit_access(request.user, contact)
    form = ContactForm(instance=contact, user=request.user)
    share_form = ShareItemForm(user=request.user)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'add_activity_comment':
            comment = (request.POST.get('activity_comment') or '').strip()
            if comment:
                _record_contact_activity(contact, request.user, 'commented', comment, kind='comment')
                messages.success(request, 'Notatka dodana.')
            else:
                messages.error(request, 'Wpisz treść notatki.')
            return redirect('contacts:view-contact', contact_id=contact.pk)

        if not can_edit_contact:
            messages.error(request, 'Nie masz uprawnień do edycji tego kontaktu.')
            return redirect('contacts:view-contact', contact_id=contact.pk)

        before = _contact_snapshot(contact)
        form = ContactForm(request.POST, instance=contact, user=request.user)
        if form.is_valid():
            form.save()
            for change in _contact_change_activities(contact, before):
                _record_contact_activity(
                    contact,
                    request.user,
                    change['action'],
                    change['message'],
                    metadata=change['metadata'],
                )
            messages.success(request, 'Kontakt zaktualizowany.')
            return redirect('contacts:view-contact', contact_id=contact.pk)
        messages.error(request, 'Nie udało się zaktualizować kontaktu.')

    if not can_edit_contact:
        for field in form.fields.values():
            field.widget.attrs['disabled'] = 'disabled'

    context = {
        'contact': contact,
        'form': form,
        'share_form': share_form,
        'can_edit_contact': can_edit_contact,
        'contact_shares': SharedItem.objects.filter(
            content_type=_content_type_for(Contact),
            object_id=contact.pk,
            shared_by=request.user,
        ).select_related('shared_with'),
        'activity_items': contact.activities.select_related('actor'),
        **_contacts_navigation_context(request.user, active_status=contact.status),
    }
    return render(request, 'contacts/view_contact.html', context)


@login_required
@require_POST
def delete_contact(request, contact_id):
    contact = get_object_or_404(Contact, pk=contact_id, user=request.user)
    contact.delete()
    messages.success(request, 'Kontakt usunięty.')
    return redirect(reverse('contacts:contacts'))


@login_required
def user_directory(request):
    query = (request.GET.get('q') or '').strip()
    user_model = get_user_model()
    users = user_model.objects.filter(is_active=True).exclude(pk=request.user.pk)

    if query:
        users = users.filter(
            Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(email__icontains=query)
            | Q(username__icontains=query)
        )
    else:
        users = users.none()

    existing_ids = set(
        UserContact.objects.filter(owner=request.user).values_list('target_user_id', flat=True)
    )

    context = {
        'query': query,
        'users': users.order_by('first_name', 'last_name', 'email')[:50],
        'existing_user_contact_ids': existing_ids,
        **_contacts_navigation_context(request.user, active_status='users'),
    }
    return render(request, 'contacts/user_directory.html', context)


@login_required
@require_POST
def add_user_contact(request, user_id):
    target_user = get_object_or_404(get_user_model(), pk=user_id, is_active=True)
    if target_user == request.user:
        messages.error(request, 'Nie możesz dodać siebie do kontaktów.')
        return redirect('contacts:user-directory')

    contact, _ = Contact.objects.get_or_create(
        user=request.user,
        email=target_user.email,
        defaults={
            'first_name': target_user.first_name,
            'last_name': target_user.last_name,
            'status': 'active',
            'source': 'Użytkownik aplikacji',
        },
    )
    user_contact, created = UserContact.objects.get_or_create(
        owner=request.user,
        target_user=target_user,
        defaults={'linked_contact': contact},
    )
    if not user_contact.linked_contact:
        user_contact.linked_contact = contact
        user_contact.save(update_fields=['linked_contact'])

    if created:
        _record_contact_activity(
            contact,
            request.user,
            'linked_user',
            'dodał użytkownika aplikacji do kontaktów',
            metadata={'email': target_user.email},
        )
        messages.success(request, 'Użytkownik dodany do kontaktów.')
    else:
        messages.info(request, 'Ten użytkownik jest już w kontaktach.')

    return redirect('contacts:user-directory')


@login_required
def companies(request):
    query = (request.GET.get('q') or '').strip()
    companies_qs = _visible_companies_queryset(request.user).annotate(contact_count=Count('contacts'))
    if query:
        companies_qs = companies_qs.filter(
            Q(name__icontains=query)
            | Q(email__icontains=query)
            | Q(phone__icontains=query)
            | Q(website__icontains=query)
        )

    context = {
        'query': query,
        'companies': companies_qs,
        **_contacts_navigation_context(request.user, active_status='companies'),
    }
    return render(request, 'contacts/companies.html', context)


@login_required
def create_company(request):
    form = CompanyForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            company = form.save(commit=False)
            company.owner = request.user
            company.save()
            CompanyMembership.objects.get_or_create(
                company=company,
                user=request.user,
                defaults={'role': 'owner'},
            )
            messages.success(request, 'Firma utworzona.')
            return redirect('contacts:view-company', company_id=company.pk)
        messages.error(request, 'Nie udało się utworzyć firmy.')

    context = {
        'form': form,
        'is_create': True,
        **_contacts_navigation_context(request.user, active_status='companies'),
    }
    return render(request, 'contacts/view_company.html', context)


@login_required
def view_company(request, company_id):
    company = get_object_or_404(_visible_companies_queryset(request.user), pk=company_id)
    can_edit_company = _has_edit_access(request.user, company)
    form = CompanyForm(request.POST or None, instance=company)
    share_form = ShareItemForm(user=request.user)

    if request.method == 'POST':
        if not can_edit_company:
            messages.error(request, 'Nie masz uprawnień do edycji tej firmy.')
            return redirect('contacts:view-company', company_id=company.pk)
        if form.is_valid():
            form.save()
            messages.success(request, 'Firma zaktualizowana.')
            return redirect('contacts:view-company', company_id=company.pk)
        messages.error(request, 'Nie udało się zaktualizować firmy.')

    if not can_edit_company:
        for field in form.fields.values():
            field.widget.attrs['disabled'] = 'disabled'

    context = {
        'company': company,
        'form': form,
        'share_form': share_form,
        'can_edit_company': can_edit_company,
        'company_contacts': company.contacts.filter(user=request.user).order_by('first_name', 'last_name'),
        'company_shares': SharedItem.objects.filter(
            content_type=_content_type_for(Company),
            object_id=company.pk,
            shared_by=request.user,
        ).select_related('shared_with'),
        **_contacts_navigation_context(request.user, active_status='companies'),
    }
    return render(request, 'contacts/view_company.html', context)


@login_required
@require_POST
def delete_company(request, company_id):
    company = get_object_or_404(Company, pk=company_id, owner=request.user)
    company.delete()
    messages.success(request, 'Firma usunięta.')
    return redirect('contacts:companies')


def _share_object(request, obj, redirect_url):
    owner = getattr(obj, 'user', None) or getattr(obj, 'owner', None)
    if owner != request.user:
        messages.error(request, 'Tylko właściciel może udostępniać ten element.')
        return redirect(redirect_url)

    form = ShareItemForm(request.POST, user=request.user)
    if form.is_valid():
        share, created = SharedItem.objects.update_or_create(
            content_type=_content_type_for(obj.__class__),
            object_id=obj.pk,
            shared_by=request.user,
            shared_with=form.cleaned_data['shared_with'],
            defaults={
                'permission': form.cleaned_data['permission'],
                'note': form.cleaned_data['note'],
            },
        )
        if created:
            messages.success(request, 'Udostępniono.')
        else:
            messages.success(request, 'Zmieniono ustawienia udostępnienia.')
    else:
        messages.error(request, 'Nie udało się udostępnić.')

    return redirect(redirect_url)


@login_required
@require_POST
def share_contact(request, contact_id):
    contact = get_object_or_404(Contact, pk=contact_id)
    return _share_object(request, contact, reverse('contacts:view-contact', args=[contact.pk]))


@login_required
@require_POST
def share_company(request, company_id):
    company = get_object_or_404(Company, pk=company_id)
    return _share_object(request, company, reverse('contacts:view-company', args=[company.pk]))


@login_required
@require_POST
def remove_share(request, share_id):
    share = get_object_or_404(SharedItem, pk=share_id, shared_by=request.user)
    target = share.content_object
    if isinstance(target, Contact):
        redirect_url = reverse('contacts:view-contact', args=[target.pk])
    elif isinstance(target, Company):
        redirect_url = reverse('contacts:view-company', args=[target.pk])
    else:
        redirect_url = reverse('contacts:shared')
    share.delete()
    messages.success(request, 'Udostępnienie usunięte.')
    return redirect(redirect_url)


@login_required
def shared_items(request):
    shares = SharedItem.objects.filter(shared_with=request.user).select_related('shared_by', 'content_type')
    context = {
        'shares': shares,
        **_contacts_navigation_context(request.user, active_status='shared'),
    }
    return render(request, 'contacts/shared_items.html', context)
