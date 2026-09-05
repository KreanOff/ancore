from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Exists, OuterRef, Prefetch, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_POST

from accounts.models import normalize_public_username
from .forms import CompanyForm, CompanyModalForm, ContactForm, ContactModalForm
from .models import Company, CompanyMembership, Contact, ContactActivity, UserContact


CONTACT_PAGE_SIZE_OPTIONS = (10, 25, 50, 100, 150, 200)
CONTACT_DEFAULT_PAGE_SIZE = 50
CONTACT_DEFAULT_SORT = 'name_asc'
CONTACT_SORT_OPTIONS = (
    {'value': 'name_asc', 'label': 'Kontakt A-Z', 'icon': 'arrow-up-a-z', 'direction': 'asc'},
    {'value': 'name_desc', 'label': 'Kontakt Z-A', 'icon': 'arrow-down-z-a', 'direction': 'desc'},
    {'value': 'company_asc', 'label': 'Firma A-Z', 'icon': 'building-2', 'direction': 'asc'},
    {'value': 'created_desc', 'label': 'Najnowsze', 'icon': 'calendar-plus', 'direction': 'desc'},
    {'value': 'created_asc', 'label': 'Najstarsze', 'icon': 'calendar-days', 'direction': 'asc'},
)
CONTACT_SORT_OPTION_MAP = {option['value']: option for option in CONTACT_SORT_OPTIONS}
COMPANY_DEFAULT_SORT = 'name_asc'
COMPANY_SORT_OPTIONS = (
    {'value': 'name_asc', 'label': 'Firma A-Z', 'icon': 'arrow-up-a-z', 'direction': 'asc'},
    {'value': 'name_desc', 'label': 'Firma Z-A', 'icon': 'arrow-down-z-a', 'direction': 'desc'},
    {'value': 'contacts_desc', 'label': 'Najwięcej kontaktów', 'icon': 'users', 'direction': 'desc'},
    {'value': 'created_desc', 'label': 'Najnowsze', 'icon': 'calendar-plus', 'direction': 'desc'},
    {'value': 'created_asc', 'label': 'Najstarsze', 'icon': 'calendar-days', 'direction': 'asc'},
)
COMPANY_SORT_OPTION_MAP = {option['value']: option for option in COMPANY_SORT_OPTIONS}


def _active_workplace(request):
    return getattr(request, 'workplace', None)


def _filter_workplace(queryset, workplace, field_name='workplace'):
    if workplace is None:
        return queryset
    return queryset.filter(**{field_name: workplace})


def _has_edit_access(user, obj):
    owner = getattr(obj, 'user', None) or getattr(obj, 'owner', None)
    return owner == user


def _visible_contacts_queryset(user, workplace=None):
    return _filter_workplace(Contact.objects.filter(user=user), workplace)


def _contacts_queryset(user, workplace=None):
    return _visible_contacts_queryset(user, workplace).annotate(
        activity_count=Count('activities')
    ).prefetch_related(
        Prefetch(
            'linked_user_contacts',
            queryset=_filter_workplace(UserContact.objects.filter(owner=user), workplace).select_related('target_user'),
            to_attr='current_user_links',
        )
    ).order_by('first_name', 'middle_name', 'last_name', 'company')


def _ancore_contacts_queryset(user, workplace=None):
    linked_user_contact = UserContact.objects.filter(linked_contact=OuterRef('pk'))
    linked_user_contact = _filter_workplace(linked_user_contact, workplace)
    return _contacts_queryset(user, workplace).annotate(
        has_ancore_login=Exists(linked_user_contact)
    ).filter(has_ancore_login=True)


def _guest_contacts_queryset(user, workplace=None):
    linked_user_contact = UserContact.objects.filter(linked_contact=OuterRef('pk'))
    linked_user_contact = _filter_workplace(linked_user_contact, workplace)
    return _contacts_queryset(user, workplace).annotate(
        has_ancore_login=Exists(linked_user_contact)
    ).filter(has_ancore_login=False)


def _contact_page_size(request):
    try:
        page_size = int(request.GET.get('page_size') or CONTACT_DEFAULT_PAGE_SIZE)
    except (TypeError, ValueError):
        return CONTACT_DEFAULT_PAGE_SIZE
    return page_size if page_size in CONTACT_PAGE_SIZE_OPTIONS else CONTACT_DEFAULT_PAGE_SIZE


def _contact_page_number(request):
    try:
        page_number = int(request.GET.get('page') or 1)
    except (TypeError, ValueError):
        return 1
    return max(page_number, 1)


def _contact_list_url(base_url, params):
    query_string = urlencode({key: value for key, value in params.items() if value not in (None, '')})
    return f'{base_url}?{query_string}' if query_string else base_url


def _contact_page_items(current_page, total_pages, base_url, base_params):
    if total_pages < 1:
        return []

    if total_pages <= 7:
        page_numbers = list(range(1, total_pages + 1))
    elif current_page <= 4:
        page_numbers = [1, 2, 3, 4, 5, total_pages]
    elif current_page >= total_pages - 3:
        page_numbers = [1, *range(total_pages - 4, total_pages + 1)]
    else:
        page_numbers = [1, current_page - 1, current_page, current_page + 1, total_pages]

    items = []
    previous_page = None
    for page_number in page_numbers:
        if previous_page and page_number - previous_page > 1:
            items.append({'is_ellipsis': True})
        params = {**base_params, 'page': page_number}
        if page_number == 1:
            params.pop('page', None)
        items.append({
            'page': page_number,
            'url': _contact_list_url(base_url, params),
            'is_current': page_number == current_page,
        })
        previous_page = page_number
    return items


def _contact_window_for_request(request, queryset, *, base_url, query='', status='', extra_params=None):
    page_size = _contact_page_size(request)
    requested_page = _contact_page_number(request)
    total_contacts = queryset.count()
    total_pages = max(1, (total_contacts + page_size - 1) // page_size)
    current_page = min(requested_page, total_pages)
    offset = (current_page - 1) * page_size
    contacts = list(queryset[offset:offset + page_size])
    base_params = {
        'q': query,
        'status': status if status not in ('', 'all', 'guests') else '',
        'page_size': page_size,
        **(extra_params or {}),
    }
    has_previous = current_page > 1 and total_contacts > 0
    has_next = current_page < total_pages and total_contacts > 0

    previous_url = ''
    if has_previous:
        previous_params = {**base_params, 'page': current_page - 1}
        if current_page - 1 == 1:
            previous_params.pop('page', None)
        previous_url = _contact_list_url(base_url, previous_params)

    next_url = ''
    if has_next:
        next_url = _contact_list_url(base_url, {**base_params, 'page': current_page + 1})

    if contacts:
        first_visible = offset + 1
        last_visible = offset + len(contacts)
        summary = f'Pokazano {first_visible}-{last_visible} z {total_contacts} kontaktów'
        compact_summary = f'{first_visible}-{last_visible} z {total_contacts}'
    else:
        summary = 'Brak kontaktów'
        compact_summary = '0 z 0'

    return {
        'contacts': contacts,
        'page': current_page,
        'total_pages': total_pages,
        'total_contacts': total_contacts,
        'page_size': page_size,
        'page_size_options': CONTACT_PAGE_SIZE_OPTIONS,
        'page_items': _contact_page_items(current_page, total_pages, base_url, base_params) if total_contacts else [],
        'has_previous': has_previous,
        'has_next': has_next,
        'previous_url': previous_url,
        'next_url': next_url,
        'summary': summary,
        'compact_summary': compact_summary,
    }


def _contact_sort_value(value):
    return value if value in CONTACT_SORT_OPTION_MAP else CONTACT_DEFAULT_SORT


def _sort_contacts(queryset, sort):
    ordering = {
        'name_asc': ('first_name', 'middle_name', 'last_name', 'company', 'id'),
        'name_desc': ('-first_name', '-middle_name', '-last_name', '-company', '-id'),
        'company_asc': ('company_record__name', 'company', 'first_name', 'last_name', 'id'),
        'created_desc': ('-created_at', '-id'),
        'created_asc': ('created_at', 'id'),
    }
    return queryset.order_by(*ordering[sort])


def _company_sort_value(value):
    return value if value in COMPANY_SORT_OPTION_MAP else COMPANY_DEFAULT_SORT


def _sort_companies(queryset, sort):
    ordering = {
        'name_asc': ('name', 'id'),
        'name_desc': ('-name', '-id'),
        'contacts_desc': ('-contact_count', 'name', 'id'),
        'created_desc': ('-created_at', '-id'),
        'created_asc': ('created_at', 'id'),
    }
    return queryset.order_by(*ordering[sort])


def _company_window_for_request(request, queryset, *, base_url, query='', contact_filter='', sort=COMPANY_DEFAULT_SORT):
    page_size = _contact_page_size(request)
    requested_page = _contact_page_number(request)
    total_companies = queryset.count()
    total_pages = max(1, (total_companies + page_size - 1) // page_size)
    current_page = min(requested_page, total_pages)
    offset = (current_page - 1) * page_size
    companies = list(queryset[offset:offset + page_size])
    base_params = {
        'q': query,
        'contact_filter': contact_filter,
        'sort': '' if sort == COMPANY_DEFAULT_SORT else sort,
        'page_size': page_size,
    }
    has_previous = current_page > 1 and total_companies > 0
    has_next = current_page < total_pages and total_companies > 0
    previous_url = ''
    next_url = ''
    if has_previous:
        previous_params = {**base_params, 'page': current_page - 1}
        if current_page - 1 == 1:
            previous_params.pop('page', None)
        previous_url = _contact_list_url(base_url, previous_params)
    if has_next:
        next_url = _contact_list_url(base_url, {**base_params, 'page': current_page + 1})

    if companies:
        first_visible = offset + 1
        last_visible = offset + len(companies)
        summary = f'Pokazano {first_visible}-{last_visible} z {total_companies} firm'
        compact_summary = f'{first_visible}-{last_visible} z {total_companies}'
    else:
        summary = 'Brak firm'
        compact_summary = '0 z 0'

    return {
        'companies': companies,
        'page': current_page,
        'total_pages': total_pages,
        'total_companies': total_companies,
        'page_size': page_size,
        'page_size_options': CONTACT_PAGE_SIZE_OPTIONS,
        'has_previous': has_previous,
        'has_next': has_next,
        'previous_url': previous_url,
        'next_url': next_url,
        'summary': summary,
        'compact_summary': compact_summary,
    }


def _contact_users_queryset(user, workplace=None):
    queryset = get_user_model().objects.filter(
        is_active=True,
        added_by_users__owner=user,
    )
    if workplace is not None:
        queryset = queryset.filter(added_by_users__workplace=workplace)
    return queryset.exclude(pk=user.pk).distinct()


def _visible_companies_queryset(user, workplace=None):
    return _filter_workplace(Company.objects.filter(owner=user), workplace).order_by('name')


def _contacts_navigation_context(user, active_status='all', active_presence='all', workplace=None):
    contacts_qs = _ancore_contacts_queryset(user, workplace)
    status_counts = {
        row['status']: row['count']
        for row in contacts_qs.values('status').annotate(count=Count('id'))
    }
    presence_counts = {
        row['presence_status']: row['count']
        for row in _contact_users_queryset(user, workplace)
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
        'total_company_count': _visible_companies_queryset(user, workplace).count(),
        'total_guest_contact_count': _guest_contacts_queryset(user, workplace).count(),
        'total_user_contact_count': _filter_workplace(UserContact.objects.filter(owner=user), workplace).count(),
        'shared_received_count': 0,
        'active_contact_status': active_status,
        'active_user_presence': active_presence,
        'contact_status_rows': status_rows,
        'contact_status_choices': Contact.STATUS_CHOICES,
        'user_presence_status_rows': presence_rows,
        'contact_modal_form': ContactModalForm(user=user, workplace=workplace),
        'company_modal_form': CompanyModalForm(),
        'contact_modal_open': False,
        'company_modal_open': False,
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


def _save_new_contact(form, user, workplace=None):
    contact = form.save(commit=False)
    contact.user = user
    contact.workplace = workplace
    contact.save()
    ancore_user = getattr(form, 'ancore_user', None)
    if ancore_user is not None and ancore_user != user:
        user_contact, _created = UserContact.objects.get_or_create(
            owner=user,
            workplace=workplace,
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


def _save_new_company(form, user, workplace=None):
    company = form.save(commit=False)
    company.owner = user
    company.workplace = workplace
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
    workplace = _active_workplace(request)
    query = (request.GET.get('q') or '').strip()
    status = (request.GET.get('status') or 'all').strip()
    contact_status = (request.GET.get('contact_status') or '').strip()
    sort = _contact_sort_value((request.GET.get('sort') or '').strip())
    contact_modal_form = ContactModalForm(user=request.user, workplace=workplace)
    company_modal_form = CompanyModalForm()
    contact_modal_open = False
    company_modal_open = False

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create_contact_modal':
            contact_modal_form = ContactModalForm(request.POST, user=request.user, workplace=workplace)
            if contact_modal_form.is_valid():
                contact = _save_new_contact(contact_modal_form, request.user, workplace)
                messages.success(request, 'Kontakt dodany.')
                return redirect('contacts:view-contact', contact_id=contact.pk)
            contact_modal_open = True
            messages.error(request, 'Nie udało się dodać kontaktu.')

        if action == 'create_company_modal':
            company_modal_form = CompanyModalForm(request.POST, request.FILES)
            if company_modal_form.is_valid():
                company = _save_new_company(company_modal_form, request.user, workplace)
                messages.success(request, 'Firma utworzona.')
                return redirect('contacts:view-company', company_id=company.pk)
            company_modal_open = True
            messages.error(request, 'Nie udało się utworzyć firmy.')

    contacts_qs = _ancore_contacts_queryset(request.user, workplace)

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
    if contact_status:
        contacts_qs = contacts_qs.filter(status=contact_status)
    contacts_qs = _sort_contacts(contacts_qs, sort)

    contact_window = _contact_window_for_request(
        request,
        contacts_qs,
        base_url=reverse('contacts:contacts'),
        query=query,
        status=status,
        extra_params={
            'contact_status': contact_status,
            'sort': '' if sort == CONTACT_DEFAULT_SORT else sort,
        },
    )

    context = {
        **_contacts_navigation_context(request.user, active_status=status, workplace=workplace),
        'contacts': contact_window['contacts'],
        'contact_window': contact_window,
        'query': query,
        'status': status,
        'contact_status_filter': contact_status,
        'contact_status_options': [
            {'value': value, 'label': label}
            for value, label in Contact.STATUS_CHOICES
        ],
        'contact_sort': sort,
        'contact_sort_param': '' if sort == CONTACT_DEFAULT_SORT else sort,
        'contact_sort_label': CONTACT_SORT_OPTION_MAP[sort]['label'],
        'contact_sort_direction': CONTACT_SORT_OPTION_MAP[sort]['direction'],
        'contact_sort_options': CONTACT_SORT_OPTIONS,
        'contact_default_sort': CONTACT_DEFAULT_SORT,
        'contact_modal_form': contact_modal_form,
        'company_modal_form': company_modal_form,
        'contact_modal_open': contact_modal_open,
        'company_modal_open': company_modal_open,
    }
    return render(request, 'contacts/contacts.html', context)


@login_required
def guest_contacts(request):
    workplace = _active_workplace(request)
    query = (request.GET.get('q') or '').strip()
    contact_status = (request.GET.get('contact_status') or '').strip()
    sort = _contact_sort_value((request.GET.get('sort') or '').strip())
    contact_modal_form = ContactModalForm(user=request.user, workplace=workplace)
    company_modal_form = CompanyModalForm()
    contact_modal_open = False
    company_modal_open = False

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create_contact_modal':
            contact_modal_form = ContactModalForm(request.POST, user=request.user, workplace=workplace)
            if contact_modal_form.is_valid():
                contact = _save_new_contact(contact_modal_form, request.user, workplace)
                messages.success(request, 'Kontakt dodany.')
                return redirect('contacts:view-contact', contact_id=contact.pk)
            contact_modal_open = True
            messages.error(request, 'Nie udało się dodać kontaktu.')

        if action == 'create_company_modal':
            company_modal_form = CompanyModalForm(request.POST, request.FILES)
            if company_modal_form.is_valid():
                company = _save_new_company(company_modal_form, request.user, workplace)
                messages.success(request, 'Firma utworzona.')
                return redirect('contacts:view-company', company_id=company.pk)
            company_modal_open = True
            messages.error(request, 'Nie udało się utworzyć firmy.')

    contacts_qs = _guest_contacts_queryset(request.user, workplace)

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
    if contact_status:
        contacts_qs = contacts_qs.filter(status=contact_status)
    contacts_qs = _sort_contacts(contacts_qs, sort)

    contact_window = _contact_window_for_request(
        request,
        contacts_qs,
        base_url=reverse('contacts:guests'),
        query=query,
        status='guests',
        extra_params={
            'contact_status': contact_status,
            'sort': '' if sort == CONTACT_DEFAULT_SORT else sort,
        },
    )

    context = {
        **_contacts_navigation_context(request.user, active_status='guests', workplace=workplace),
        'contacts': contact_window['contacts'],
        'contact_window': contact_window,
        'query': query,
        'status': 'guests',
        'contact_status_filter': contact_status,
        'contact_status_options': [
            {'value': value, 'label': label}
            for value, label in Contact.STATUS_CHOICES
        ],
        'contact_sort': sort,
        'contact_sort_param': '' if sort == CONTACT_DEFAULT_SORT else sort,
        'contact_sort_label': CONTACT_SORT_OPTION_MAP[sort]['label'],
        'contact_sort_direction': CONTACT_SORT_OPTION_MAP[sort]['direction'],
        'contact_sort_options': CONTACT_SORT_OPTIONS,
        'contact_default_sort': CONTACT_DEFAULT_SORT,
        'contacts_page_title': 'Goście',
        'contacts_page_label': 'Lista gości',
        'contacts_search_placeholder': 'Szukaj gościa',
        'contacts_empty_heading': 'Brak gości',
        'contacts_empty_copy': 'Kontakty bez ID Ancore pojawią się tutaj.',
        'contact_modal_form': contact_modal_form,
        'company_modal_form': company_modal_form,
        'contact_modal_open': contact_modal_open,
        'company_modal_open': company_modal_open,
    }
    return render(request, 'contacts/contacts.html', context)


def _contact_detail_queryset(user, workplace=None):
    return _visible_contacts_queryset(user, workplace).prefetch_related(
        'activities__actor',
        Prefetch(
            'linked_user_contacts',
            queryset=_filter_workplace(UserContact.objects.filter(owner=user), workplace).select_related('target_user'),
            to_attr='current_user_links',
        ),
    )


@login_required
def view_contact(request, contact_id):
    workplace = _active_workplace(request)
    contact = get_object_or_404(_contact_detail_queryset(request.user, workplace), pk=contact_id)
    can_edit_contact = _has_edit_access(request.user, contact)

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
        'can_edit_contact': can_edit_contact,
        'contact_shares': [],
        'activity_items': contact.activities.select_related('actor'),
        **_contacts_navigation_context(request.user, active_status=contact.status, workplace=workplace),
    }
    return render(request, 'contacts/view_contact.html', context)


@login_required
def edit_contact(request, contact_id):
    workplace = _active_workplace(request)
    contact = get_object_or_404(_contact_detail_queryset(request.user, workplace), pk=contact_id)
    can_edit_contact = _has_edit_access(request.user, contact)

    if not can_edit_contact:
        messages.error(request, 'Nie masz uprawnień do edycji tego kontaktu.')
        return redirect('contacts:view-contact', contact_id=contact.pk)

    form = ContactForm(request.POST or None, instance=contact, user=request.user, workplace=workplace)

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
        'can_edit_contact': can_edit_contact,
        'contact_shares': [],
        'activity_items': contact.activities.select_related('actor'),
        **_contacts_navigation_context(request.user, active_status=contact.status, workplace=workplace),
    }
    return render(request, 'contacts/view_contact.html', context)


@login_required
@require_POST
def delete_contact(request, contact_id):
    contact = get_object_or_404(_filter_workplace(Contact.objects.filter(user=request.user), _active_workplace(request)), pk=contact_id)
    contact.delete()
    messages.success(request, 'Kontakt usunięty.')
    return redirect(reverse('contacts:contacts'))


@login_required
def user_directory(request):
    workplace = _active_workplace(request)
    query = (request.GET.get('q') or '').strip()
    presence = (request.GET.get('presence') or 'all').strip()
    user_model = get_user_model()
    valid_presence_statuses = {value for value, _label in user_model.PresenceStatus.choices}
    if presence not in valid_presence_statuses:
        presence = 'all'

    users = user_model.objects.filter(is_active=True).exclude(pk=request.user.pk)
    if presence != 'all':
        users = users.filter(added_by_users__owner=request.user)
        if workplace is not None:
            users = users.filter(added_by_users__workplace=workplace)
        users = users.distinct()

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
        _filter_workplace(UserContact.objects.filter(owner=request.user), workplace).values_list('target_user_id', flat=True)
    )

    context = {
        'query': query,
        'presence': presence,
        'users': users.order_by('first_name', 'middle_name', 'last_name', 'email')[:50],
        'existing_user_contact_ids': existing_ids,
        **_contacts_navigation_context(request.user, active_status='users', active_presence=presence, workplace=workplace),
    }
    return render(request, 'contacts/user_directory.html', context)


@login_required
@require_POST
def add_user_contact(request, user_id):
    workplace = _active_workplace(request)
    target_user = get_object_or_404(get_user_model(), pk=user_id, is_active=True)
    if target_user == request.user:
        messages.error(request, 'Nie możesz dodać siebie do kontaktów.')
        return redirect('contacts:user-directory')

    contact, _ = Contact.objects.get_or_create(
        user=request.user,
        workplace=workplace,
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
        workplace=workplace,
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
    workplace = _active_workplace(request)
    query = (request.GET.get('q') or '').strip()
    contact_filter = (request.GET.get('contact_filter') or '').strip()
    sort = _company_sort_value((request.GET.get('sort') or '').strip())
    contact_modal_form = ContactModalForm(user=request.user, workplace=workplace)
    company_modal_form = CompanyModalForm()
    contact_modal_open = False
    company_modal_open = False

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create_contact_modal':
            contact_modal_form = ContactModalForm(request.POST, user=request.user, workplace=workplace)
            if contact_modal_form.is_valid():
                contact = _save_new_contact(contact_modal_form, request.user, workplace)
                messages.success(request, 'Kontakt dodany.')
                return redirect('contacts:view-contact', contact_id=contact.pk)
            contact_modal_open = True
            messages.error(request, 'Nie udało się dodać kontaktu.')

        if action == 'create_company_modal':
            company_modal_form = CompanyModalForm(request.POST, request.FILES)
            if company_modal_form.is_valid():
                company = _save_new_company(company_modal_form, request.user, workplace)
                messages.success(request, 'Firma utworzona.')
                return redirect('contacts:view-company', company_id=company.pk)
            company_modal_open = True
            messages.error(request, 'Nie udało się utworzyć firmy.')

    companies_qs = _visible_companies_queryset(request.user, workplace).annotate(contact_count=Count('contacts', filter=Q(contacts__workplace=workplace)))
    if query:
        companies_qs = companies_qs.filter(
            Q(name__icontains=query)
            | Q(email__icontains=query)
            | Q(phone__icontains=query)
            | Q(website__icontains=query)
        )
    if contact_filter == 'with_contacts':
        companies_qs = companies_qs.filter(contact_count__gt=0)
    elif contact_filter == 'without_contacts':
        companies_qs = companies_qs.filter(contact_count=0)
    companies_qs = _sort_companies(companies_qs, sort)
    company_window = _company_window_for_request(
        request,
        companies_qs,
        base_url=reverse('contacts:companies'),
        query=query,
        contact_filter=contact_filter,
        sort=sort,
    )

    context = {
        **_contacts_navigation_context(request.user, active_status='companies', workplace=workplace),
        'query': query,
        'companies': company_window['companies'],
        'company_window': company_window,
        'company_contact_filter': contact_filter,
        'company_contact_filter_options': (
            {'value': 'with_contacts', 'label': 'Z kontaktami'},
            {'value': 'without_contacts', 'label': 'Bez kontaktów'},
        ),
        'company_sort': sort,
        'company_sort_param': '' if sort == COMPANY_DEFAULT_SORT else sort,
        'company_sort_label': COMPANY_SORT_OPTION_MAP[sort]['label'],
        'company_sort_direction': COMPANY_SORT_OPTION_MAP[sort]['direction'],
        'company_sort_options': COMPANY_SORT_OPTIONS,
        'company_default_sort': COMPANY_DEFAULT_SORT,
        'contact_modal_form': contact_modal_form,
        'company_modal_form': company_modal_form,
        'contact_modal_open': contact_modal_open,
        'company_modal_open': company_modal_open,
    }
    return render(request, 'contacts/companies.html', context)


@login_required
def view_company(request, company_id):
    workplace = _active_workplace(request)
    company = get_object_or_404(_visible_companies_queryset(request.user, workplace), pk=company_id)
    can_edit_company = _has_edit_access(request.user, company)
    company_contacts = _contacts_queryset(request.user, workplace).filter(company_record=company)

    if request.method == 'POST':
        messages.error(request, 'Edycja firmy jest dostępna w osobnym widoku.')
        return redirect('contacts:view-company', company_id=company.pk)

    context = {
        'company': company,
        'can_edit_company': can_edit_company,
        'company_contacts': company_contacts,
        'company_shares': [],
        **_contacts_navigation_context(request.user, active_status='companies', workplace=workplace),
    }
    return render(request, 'contacts/view_company.html', context)


@login_required
def edit_company(request, company_id):
    workplace = _active_workplace(request)
    company = get_object_or_404(_visible_companies_queryset(request.user, workplace), pk=company_id)
    can_edit_company = _has_edit_access(request.user, company)

    if not can_edit_company:
        messages.error(request, 'Nie masz uprawnień do edycji tej firmy.')
        return redirect('contacts:view-company', company_id=company.pk)

    form = CompanyForm(request.POST or None, request.FILES or None, instance=company)

    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, 'Firma zaktualizowana.')
            return redirect('contacts:view-company', company_id=company.pk)
        messages.error(request, 'Nie udało się zaktualizować firmy.')

    company_contacts = _contacts_queryset(request.user, workplace).filter(company_record=company)

    context = {
        'company': company,
        'form': form,
        'is_edit': True,
        'can_edit_company': can_edit_company,
        'company_contacts': company_contacts,
        'company_shares': [],
        **_contacts_navigation_context(request.user, active_status='companies', workplace=workplace),
    }
    return render(request, 'contacts/view_company.html', context)


@login_required
@require_POST
def delete_company(request, company_id):
    company = get_object_or_404(_filter_workplace(Company.objects.filter(owner=request.user), _active_workplace(request)), pk=company_id)
    company.delete()
    messages.success(request, 'Firma usunięta.')
    return redirect('contacts:companies')
