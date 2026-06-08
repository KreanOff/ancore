from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.db.models import Count, Exists, OuterRef, Prefetch, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_POST

from accounts.models import normalize_public_username
from .forms import CompanyForm, CompanyModalForm, ContactForm, ContactModalForm, ShareItemForm
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
    ).prefetch_related(
        Prefetch(
            'linked_user_contacts',
            queryset=UserContact.objects.filter(owner=user).select_related('target_user'),
            to_attr='current_user_links',
        )
    ).order_by('first_name', 'middle_name', 'last_name', 'company')


def _ancore_contacts_queryset(user):
    linked_user_contact = UserContact.objects.filter(linked_contact=OuterRef('pk'))
    return _contacts_queryset(user).annotate(
        has_ancore_login=Exists(linked_user_contact)
    ).filter(has_ancore_login=True)


def _guest_contacts_queryset(user):
    linked_user_contact = UserContact.objects.filter(linked_contact=OuterRef('pk'))
    return _contacts_queryset(user).annotate(
        has_ancore_login=Exists(linked_user_contact)
    ).filter(has_ancore_login=False)


def _contact_users_queryset(user):
    return get_user_model().objects.filter(
        is_active=True,
        added_by_users__owner=user,
    ).exclude(pk=user.pk).distinct()


def _visible_companies_queryset(user):
    return Company.objects.filter(
        Q(owner=user) | Q(pk__in=_shared_object_ids(user, Company))
    ).distinct().order_by('name')


def _contacts_navigation_context(user, active_status='all', active_presence='all'):
    contacts_qs = _ancore_contacts_queryset(user)
    status_counts = {
        row['status']: row['count']
        for row in contacts_qs.values('status').annotate(count=Count('id'))
    }
    presence_counts = {
        row['presence_status']: row['count']
        for row in _contact_users_queryset(user)
        .values('presence_status')
        .annotate(count=Count('id'))
    }
    status_rows = [
        {
            'value': value,
            'label': label,
            'count': status_counts.get(value, 0),
        }
        for value, label in Contact.STATUS_CHOICES
    ]
    presence_rows = [
        {
            'value': value,
            'label': label,
            'count': presence_counts.get(value, 0),
        }
        for value, label in get_user_model().PresenceStatus.choices
    ]
    return {
        'contacts_nav': contacts_qs[:30],
        'total_contact_count': contacts_qs.count(),
        'total_company_count': _visible_companies_queryset(user).count(),
        'total_guest_contact_count': _guest_contacts_queryset(user).count(),
        'total_user_contact_count': UserContact.objects.filter(owner=user).count(),
        'shared_received_count': SharedItem.objects.filter(shared_with=user).count(),
        'active_contact_status': active_status,
        'active_user_presence': active_presence,
        'contact_status_rows': status_rows,
        'contact_status_choices': Contact.STATUS_CHOICES,
        'user_presence_status_rows': presence_rows,
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


def _save_new_contact(form, user):
    contact = form.save(commit=False)
    contact.user = user
    contact.save()
    ancore_user = getattr(form, 'ancore_user', None)
    if ancore_user is not None and ancore_user != user:
        user_contact, _created = UserContact.objects.get_or_create(
            owner=user,
            target_user=ancore_user,
            defaults={'linked_contact': contact},
        )
        if not user_contact.linked_contact:
            user_contact.linked_contact = contact
            user_contact.save(update_fields=['linked_contact'])
    _record_contact_activity(
        contact,
        user,
        'created',
        'utworzył kontakt',
        metadata={'title': contact.display_name},
    )
    if ancore_user is not None and ancore_user != user:
        _record_contact_activity(
            contact,
            user,
            'linked_user',
            'dodał użytkownika aplikacji do kontaktów',
            metadata={'email': ancore_user.email, 'username': ancore_user.username},
        )
    return contact


def _save_new_company(form, user):
    company = form.save(commit=False)
    company.owner = user
    company.save()
    CompanyMembership.objects.get_or_create(
        company=company,
        user=user,
        defaults={'role': 'owner'},
    )
    return company


def _contact_snapshot(contact):
    return {
        'first_name': contact.first_name,
        'middle_name': contact.middle_name,
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
        'middle_name': 'drugie imię',
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
@require_GET
def lookup_ancore_login(request):
    login = normalize_public_username(request.GET.get('login') or request.GET.get('q') or '')
    if not login:
        return JsonResponse({'found': False})

    user_model = get_user_model()
    user = (
        user_model.objects
        .filter(is_active=True, username__iexact=login)
        .exclude(pk=request.user.pk)
        .first()
    )
    if user is None:
        return JsonResponse({'found': False})

    return JsonResponse({
        'found': True,
        'user': {
            'username': user.username,
            'first_name': user.first_name,
            'middle_name': user.middle_name,
            'last_name': user.last_name,
            'email': user.email,
            'phone': user.phone_number,
            'role': user.job_title,
            'source': 'Użytkownik aplikacji',
            'status': 'active',
        },
    })


@login_required
def contacts(request):
    query = (request.GET.get('q') or '').strip()
    status = (request.GET.get('status') or 'all').strip()
    contact_modal_form = ContactModalForm(user=request.user)
    company_modal_form = CompanyModalForm()
    contact_modal_open = False
    company_modal_open = False

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create_contact_modal':
            contact_modal_form = ContactModalForm(request.POST, user=request.user)
            if contact_modal_form.is_valid():
                contact = _save_new_contact(contact_modal_form, request.user)
                messages.success(request, 'Kontakt dodany.')
                return redirect('contacts:view-contact', contact_id=contact.pk)
            contact_modal_open = True
            messages.error(request, 'Nie udało się dodać kontaktu.')

        if action == 'create_company_modal':
            company_modal_form = CompanyModalForm(request.POST)
            if company_modal_form.is_valid():
                company = _save_new_company(company_modal_form, request.user)
                messages.success(request, 'Firma utworzona.')
                return redirect('contacts:view-company', company_id=company.pk)
            company_modal_open = True
            messages.error(request, 'Nie udało się utworzyć firmy.')

    contacts_qs = _ancore_contacts_queryset(request.user)

    if query:
        contacts_qs = contacts_qs.filter(
            Q(first_name__icontains=query)
            | Q(middle_name__icontains=query)
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
        'contact_modal_form': contact_modal_form,
        'company_modal_form': company_modal_form,
        'contact_modal_open': contact_modal_open,
        'company_modal_open': company_modal_open,
        **_contacts_navigation_context(request.user, active_status=status),
    }
    return render(request, 'contacts/contacts.html', context)


@login_required
def guest_contacts(request):
    query = (request.GET.get('q') or '').strip()
    contact_modal_form = ContactModalForm(user=request.user)
    company_modal_form = CompanyModalForm()
    contact_modal_open = False
    company_modal_open = False

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create_contact_modal':
            contact_modal_form = ContactModalForm(request.POST, user=request.user)
            if contact_modal_form.is_valid():
                contact = _save_new_contact(contact_modal_form, request.user)
                messages.success(request, 'Kontakt dodany.')
                return redirect('contacts:view-contact', contact_id=contact.pk)
            contact_modal_open = True
            messages.error(request, 'Nie udało się dodać kontaktu.')

        if action == 'create_company_modal':
            company_modal_form = CompanyModalForm(request.POST)
            if company_modal_form.is_valid():
                company = _save_new_company(company_modal_form, request.user)
                messages.success(request, 'Firma utworzona.')
                return redirect('contacts:view-company', company_id=company.pk)
            company_modal_open = True
            messages.error(request, 'Nie udało się utworzyć firmy.')

    contacts_qs = _guest_contacts_queryset(request.user)

    if query:
        contacts_qs = contacts_qs.filter(
            Q(first_name__icontains=query)
            | Q(middle_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(company__icontains=query)
            | Q(company_record__name__icontains=query)
            | Q(email__icontains=query)
            | Q(phone__icontains=query)
        )

    context = {
        'contacts': contacts_qs,
        'query': query,
        'status': 'guests',
        'contacts_page_title': 'Goście',
        'contacts_page_label': 'Lista gości',
        'contacts_search_placeholder': 'Szukaj gościa',
        'contacts_empty_heading': 'Brak gości',
        'contacts_empty_copy': 'Kontakty bez ID Ancore pojawią się tutaj.',
        'contact_modal_form': contact_modal_form,
        'company_modal_form': company_modal_form,
        'contact_modal_open': contact_modal_open,
        'company_modal_open': company_modal_open,
        **_contacts_navigation_context(request.user, active_status='guests'),
    }
    return render(request, 'contacts/contacts.html', context)


@login_required
def create_contact(request):
    form = ContactForm(request.POST or None, user=request.user)
    if request.method == 'POST':
        if form.is_valid():
            contact = _save_new_contact(form, request.user)
            messages.success(request, 'Kontakt dodany.')
            return redirect('contacts:view-contact', contact_id=contact.pk)
        messages.error(request, 'Nie udało się dodać kontaktu.')

    context = {
        'form': form,
        'is_create': True,
        **_contacts_navigation_context(request.user),
    }
    return render(request, 'contacts/view_contact.html', context)


def _contact_detail_queryset(user):
    return _visible_contacts_queryset(user).prefetch_related(
        'activities__actor',
        Prefetch(
            'linked_user_contacts',
            queryset=UserContact.objects.filter(owner=user).select_related('target_user'),
            to_attr='current_user_links',
        ),
    )


@login_required
def view_contact(request, contact_id):
    contact = get_object_or_404(_contact_detail_queryset(request.user), pk=contact_id)
    can_edit_contact = _has_edit_access(request.user, contact)
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

        messages.error(request, 'Edycja kontaktu jest dostępna w osobnym widoku.')
        return redirect('contacts:view-contact', contact_id=contact.pk)

    context = {
        'contact': contact,
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
def edit_contact(request, contact_id):
    contact = get_object_or_404(_contact_detail_queryset(request.user), pk=contact_id)
    can_edit_contact = _has_edit_access(request.user, contact)

    if not can_edit_contact:
        messages.error(request, 'Nie masz uprawnień do edycji tego kontaktu.')
        return redirect('contacts:view-contact', contact_id=contact.pk)

    form = ContactForm(request.POST or None, instance=contact, user=request.user)

    if request.method == 'POST':
        before = _contact_snapshot(contact)
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

    context = {
        'contact': contact,
        'form': form,
        'is_edit': True,
        'share_form': ShareItemForm(user=request.user),
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
    presence = (request.GET.get('presence') or 'all').strip()
    user_model = get_user_model()
    valid_presence_statuses = {value for value, _label in user_model.PresenceStatus.choices}
    if presence not in valid_presence_statuses:
        presence = 'all'

    users = user_model.objects.filter(is_active=True).exclude(pk=request.user.pk)
    if presence != 'all':
        users = users.filter(added_by_users__owner=request.user).distinct()

    if query:
        users = users.filter(
            Q(first_name__icontains=query)
            | Q(middle_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(email__icontains=query)
            | Q(username__icontains=query)
        )
    if presence != 'all':
        users = users.filter(presence_status=presence)

    if not query and presence == 'all':
        users = users.none()

    existing_ids = set(
        UserContact.objects.filter(owner=request.user).values_list('target_user_id', flat=True)
    )

    context = {
        'query': query,
        'presence': presence,
        'users': users.order_by('first_name', 'middle_name', 'last_name', 'email')[:50],
        'existing_user_contact_ids': existing_ids,
        **_contacts_navigation_context(request.user, active_status='users', active_presence=presence),
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
            'middle_name': target_user.middle_name,
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
    contact_modal_form = ContactModalForm(user=request.user)
    company_modal_form = CompanyModalForm()
    contact_modal_open = False
    company_modal_open = False

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create_contact_modal':
            contact_modal_form = ContactModalForm(request.POST, user=request.user)
            if contact_modal_form.is_valid():
                contact = _save_new_contact(contact_modal_form, request.user)
                messages.success(request, 'Kontakt dodany.')
                return redirect('contacts:view-contact', contact_id=contact.pk)
            contact_modal_open = True
            messages.error(request, 'Nie udało się dodać kontaktu.')

        if action == 'create_company_modal':
            company_modal_form = CompanyModalForm(request.POST)
            if company_modal_form.is_valid():
                company = _save_new_company(company_modal_form, request.user)
                messages.success(request, 'Firma utworzona.')
                return redirect('contacts:view-company', company_id=company.pk)
            company_modal_open = True
            messages.error(request, 'Nie udało się utworzyć firmy.')

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
        'contact_modal_form': contact_modal_form,
        'company_modal_form': company_modal_form,
        'contact_modal_open': contact_modal_open,
        'company_modal_open': company_modal_open,
        **_contacts_navigation_context(request.user, active_status='companies'),
    }
    return render(request, 'contacts/companies.html', context)


@login_required
def create_company(request):
    form = CompanyForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            company = _save_new_company(form, request.user)
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
        'company_contacts': company.contacts.filter(user=request.user).order_by('first_name', 'middle_name', 'last_name'),
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
