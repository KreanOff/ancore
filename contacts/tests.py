from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse

from .models import Company, Contact, SharedItem, UserContact
from .templatetags.company_avatar import company_avatar


class ContactCollaborationTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.owner = user_model.objects.create_user(
            username='@anna.kowalska',
            email='anna@example.com',
            first_name='Anna',
            last_name='Kowalska',
            password='test-pass-123',
        )
        self.other_user = user_model.objects.create_user(
            username='@marek.nowak',
            email='marek@example.com',
            first_name='Marek',
            last_name='Nowak',
            password='test-pass-123',
        )
        self.other_user.profile_photo = 'profile_photos/marek.webp'
        self.other_user.phone_number = '+48 111 222 333'
        self.other_user.job_title = 'Project Manager'
        self.other_user.save(update_fields=['profile_photo', 'phone_number', 'job_title'])
        self.busy_user = user_model.objects.create_user(
            username='@jan.zajety',
            email='jan@example.com',
            first_name='Jan',
            last_name='Zajety',
            password='test-pass-123',
            presence_status=user_model.PresenceStatus.BUSY,
        )
        self.client.force_login(self.owner)

    def test_user_directory_search_adds_application_user_as_contact(self):
        response = self.client.get(reverse('contacts:user-directory'), {'q': '@marek.nowak'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '@marek.nowak')
        self.assertContains(response, 'marek@example.com')
        self.assertContains(response, '/media/profile_photos/marek.webp')

        response = self.client.post(reverse('contacts:add-user-contact', args=[self.other_user.pk]))

        self.assertRedirects(response, reverse('contacts:user-directory'))
        self.assertTrue(UserContact.objects.filter(owner=self.owner, target_user=self.other_user).exists())
        contact = Contact.objects.get(user=self.owner, email='marek@example.com')
        self.assertEqual(contact.first_name, 'Marek')
        self.assertEqual(contact.status, 'active')

        response = self.client.get(reverse('contacts:contacts'))
        self.assertContains(response, '/media/profile_photos/marek.webp')

    def test_guest_contacts_list_shows_contacts_without_ancore_login(self):
        guest = Contact.objects.create(
            user=self.owner,
            first_name='Ola',
            last_name='Gosc',
            email='ola.gosc@example.com',
        )
        linked_contact = Contact.objects.create(
            user=self.owner,
            first_name='Marek',
            last_name='Nowak',
            email='marek@example.com',
            status='active',
        )
        UserContact.objects.create(
            owner=self.owner,
            target_user=self.other_user,
            linked_contact=linked_contact,
        )

        response = self.client.get(reverse('contacts:contacts'))

        self.assertEqual(response.context['total_contact_count'], 1)
        self.assertEqual(response.context['total_guest_contact_count'], 1)
        self.assertContains(response, reverse('contacts:guests'))
        self.assertContains(response, 'Goście')
        self.assertEqual(list(response.context['contacts']), [linked_contact])

        response = self.client.get(reverse('contacts:guests'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Goście')
        self.assertEqual(list(response.context['contacts']), [guest])

    def test_presence_navigation_counts_only_added_user_contacts(self):
        response = self.client.get(reverse('contacts:contacts'))

        self.assertEqual(response.status_code, 200)
        presence_counts = {
            row['value']: row['count']
            for row in response.context['user_presence_status_rows']
        }
        self.assertEqual(presence_counts['active'], 0)
        self.assertEqual(presence_counts['busy'], 0)

        response = self.client.get(reverse('contacts:user-directory'), {'presence': 'busy'})

        self.assertNotContains(response, 'Jan')

    def test_user_directory_can_filter_added_contacts_by_presence_status(self):
        contact = Contact.objects.create(
            user=self.owner,
            first_name='Jan',
            last_name='Zajety',
            email='jan@example.com',
            status='active',
        )
        UserContact.objects.create(
            owner=self.owner,
            target_user=self.busy_user,
            linked_contact=contact,
        )

        response = self.client.get(reverse('contacts:user-directory'), {'presence': 'busy'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Jan')
        self.assertContains(response, 'Zajęty')
        self.assertContains(response, 'contacts-presence-list')
        self.assertNotContains(response, 'Marek')

    def test_linked_user_contact_shows_current_presence_status(self):
        contact = Contact.objects.create(
            user=self.owner,
            first_name='Jan',
            last_name='Zajety',
            email='jan@example.com',
            status='active',
        )
        UserContact.objects.create(
            owner=self.owner,
            target_user=self.busy_user,
            linked_contact=contact,
        )

        response = self.client.get(reverse('contacts:contacts'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'profile-presence-badge presence-busy')
        self.assertContains(response, 'Zajęty')
        self.assertNotContains(response, 'contacts-status-active">Aktywny')

        self.busy_user.presence_status = get_user_model().PresenceStatus.DO_NOT_DISTURB
        self.busy_user.save(update_fields=['presence_status'])
        response = self.client.get(reverse('contacts:contacts'))

        self.assertContains(response, 'profile-presence-badge presence-do_not_disturb')
        self.assertContains(response, 'Nie przeszkadzać')
        self.assertNotContains(response, 'profile-presence-badge presence-busy')

    def test_company_can_be_created_and_linked_to_contact(self):
        response = self.client.post(reverse('contacts:create-company'), {
            'name': 'Acme',
            'website': 'https://acme.example.com',
            'email': 'hello@acme.example.com',
            'phone': '',
            'address': '',
            'notes': 'Ważny klient',
        })

        company = Company.objects.get(owner=self.owner, name='Acme')
        self.assertRedirects(response, reverse('contacts:view-company', args=[company.pk]))

        response = self.client.post(reverse('contacts:create'), {
            'first_name': 'Ewa',
            'last_name': 'Lis',
            'company': '',
            'company_record': company.pk,
            'role': 'CEO',
            'email': 'ewa@acme.example.com',
            'phone': '',
            'source': '',
            'last_contacted_at': '',
            'notes': '',
        })

        contact = Contact.objects.get(user=self.owner, email='ewa@acme.example.com')
        self.assertRedirects(response, reverse('contacts:view-contact', args=[contact.pk]))
        self.assertEqual(contact.company_record, company)
        self.assertEqual(contact.company, 'Acme')

    def test_contacts_page_exposes_modal_create_forms(self):
        response = self.client.get(reverse('contacts:contacts'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="contact-create-modal"')
        self.assertContains(response, 'id="company-create-modal"')
        self.assertContains(response, 'data-open-contact')
        self.assertContains(response, 'data-open-company')
        self.assertContains(response, 'value="create_contact_modal"')
        self.assertContains(response, 'value="create_company_modal"')
        self.assertContains(response, 'ID Ancore')
        self.assertContains(response, reverse('contacts:lookup-ancore-login'))
        self.assertNotIn('status', response.context['contact_modal_form'].fields)

    def test_company_avatar_uses_company_specific_background_color(self):
        company = Company.objects.create(owner=self.owner, name='Netology')
        other_company = Company.objects.create(owner=self.owner, name='Ancore Labs')

        avatar = company_avatar(company)
        other_avatar = company_avatar(other_company)

        self.assertEqual(avatar['background_color'], company_avatar(company)['background_color'])
        self.assertNotEqual(avatar['background_color'], other_avatar['background_color'])
        self.assertIn('--profile-avatar-bg:', avatar['color_style'])

        response = self.client.get(reverse('contacts:companies'))

        self.assertContains(response, avatar['color_style'])
        self.assertContains(response, other_avatar['color_style'])

    def test_ancore_login_lookup_returns_user_payload(self):
        response = self.client.get(reverse('contacts:lookup-ancore-login'), {'login': 'marek.nowak'})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload['found'])
        self.assertEqual(payload['user']['username'], '@marek.nowak')
        self.assertEqual(payload['user']['first_name'], 'Marek')
        self.assertEqual(payload['user']['last_name'], 'Nowak')
        self.assertEqual(payload['user']['email'], 'marek@example.com')
        self.assertEqual(payload['user']['phone'], '+48 111 222 333')
        self.assertEqual(payload['user']['role'], 'Project Manager')
        self.assertEqual(payload['user']['source'], 'Użytkownik aplikacji')
        self.assertEqual(payload['user']['status'], 'active')

    def test_modal_contact_post_with_ancore_login_autofills_and_links_user(self):
        response = self.client.post(reverse('contacts:contacts'), {
            'action': 'create_contact_modal',
            'ancore_login': '@marek.nowak',
            'first_name': '',
            'last_name': '',
            'company': '',
            'company_record': '',
            'role': '',
            'email': '',
            'phone': '',
            'source': '',
            'last_contacted_at': '',
            'notes': '',
        })

        contact = Contact.objects.get(user=self.owner, email='marek@example.com')
        self.assertRedirects(response, reverse('contacts:view-contact', args=[contact.pk]))
        self.assertEqual(contact.first_name, 'Marek')
        self.assertEqual(contact.last_name, 'Nowak')
        self.assertEqual(contact.phone, '+48 111 222 333')
        self.assertEqual(contact.role, 'Project Manager')
        self.assertEqual(contact.source, 'Użytkownik aplikacji')
        self.assertEqual(contact.status, 'active')
        self.assertTrue(UserContact.objects.filter(
            owner=self.owner,
            target_user=self.other_user,
            linked_contact=contact,
        ).exists())

    def test_invalid_modal_contact_post_reopens_contact_modal(self):
        response = self.client.post(reverse('contacts:contacts'), {
            'action': 'create_contact_modal',
            'ancore_login': '',
            'first_name': '',
            'last_name': '',
            'company': '',
            'company_record': '',
            'role': '',
            'email': '',
            'phone': '',
            'source': '',
            'last_contacted_at': '',
            'notes': '',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="contact-create-modal"')
        self.assertContains(response, 'is-open')
        self.assertContains(response, 'Podaj imię albo firmę.')

    def test_invalid_modal_company_post_reopens_company_modal(self):
        response = self.client.post(reverse('contacts:companies'), {
            'action': 'create_company_modal',
            'name': '',
            'website': '',
            'email': '',
            'phone': '',
            'address': '',
            'notes': '',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="company-create-modal"')
        self.assertContains(response, 'is-open')
        self.assertContains(response, 'To pole jest wymagane.')

    def test_shared_contact_is_visible_to_recipient(self):
        contact = Contact.objects.create(
            user=self.owner,
            first_name='Kamil',
            last_name='Testowy',
            email='kamil@example.com',
        )
        SharedItem.objects.create(
            content_type=ContentType.objects.get_for_model(Contact),
            object_id=contact.pk,
            shared_by=self.owner,
            shared_with=self.other_user,
            permission='view',
        )

        self.client.force_login(self.other_user)
        response = self.client.get(reverse('contacts:view-contact', args=[contact.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Kamil')
        self.assertNotContains(response, 'Zapisz')

    def test_contact_detail_is_read_only_and_links_to_edit(self):
        contact = Contact.objects.create(
            user=self.owner,
            first_name='Ewa',
            last_name='Lis',
            email='ewa@example.com',
            phone='+48 500 600 700',
            notes='Rozmowa po demo.',
        )

        response = self.client.get(reverse('contacts:view-contact', args=[contact.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ewa Lis')
        self.assertContains(response, 'ewa@example.com')
        self.assertContains(response, reverse('contacts:edit-contact', args=[contact.pk]))
        self.assertContains(response, 'Edytuj')
        self.assertContains(response, 'data-contact-actions')
        self.assertContains(response, 'tasks-icon-button contacts-actions-menu__toggle')
        self.assertContains(response, 'M18 12h.01')
        self.assertContains(response, 'Opcje kontaktu')
        self.assertContains(response, 'Usuń')
        self.assertContains(response, 'profile-summary')
        self.assertContains(response, 'profile-display-name')
        self.assertContains(response, 'profile-issue-sidebar')
        self.assertNotContains(response, 'id="contact-detail-form"')
        self.assertNotContains(response, 'name="first_name"')
        self.assertNotContains(response, 'Zapisz')
        self.assertNotContains(response, 'contacts-delete-button')

    def test_contact_detail_post_does_not_update_contact_fields(self):
        contact = Contact.objects.create(
            user=self.owner,
            first_name='Kamil',
            last_name='Testowy',
            email='kamil@example.com',
        )

        response = self.client.post(reverse('contacts:view-contact', args=[contact.pk]), {
            'first_name': 'Zmieniony',
            'last_name': 'Testowy',
            'company': '',
            'company_record': '',
            'role': '',
            'email': 'changed@example.com',
            'phone': '',
            'source': '',
            'last_contacted_at': '',
            'notes': '',
        })

        contact.refresh_from_db()
        self.assertRedirects(response, reverse('contacts:view-contact', args=[contact.pk]))
        self.assertEqual(contact.first_name, 'Kamil')
        self.assertEqual(contact.email, 'kamil@example.com')

    def test_contact_edit_page_updates_contact_fields(self):
        contact = Contact.objects.create(
            user=self.owner,
            first_name='Kamil',
            last_name='Testowy',
            email='kamil@example.com',
        )

        response = self.client.get(reverse('contacts:edit-contact', args=[contact.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="contact-detail-form"')
        self.assertContains(response, 'contacts-edit-modal is-open')
        self.assertContains(response, 'contacts-edit-modal__dialog')
        self.assertContains(response, 'tasks-modal__form tasks-issue-modal__form contacts-edit-form')
        self.assertContains(response, 'contacts-edit-modal__body')
        self.assertContains(response, 'Zapisz')

        response = self.client.post(reverse('contacts:edit-contact', args=[contact.pk]), {
            'first_name': 'Karol',
            'last_name': 'Testowy',
            'company': 'Ancore',
            'company_record': '',
            'role': 'Konsultant',
            'email': 'karol@example.com',
            'phone': '+48 123 456 789',
            'source': 'Polecenie',
            'last_contacted_at': '',
            'notes': 'Przeniesione do osobnej edycji.',
        })

        contact.refresh_from_db()
        self.assertRedirects(response, reverse('contacts:view-contact', args=[contact.pk]))
        self.assertEqual(contact.first_name, 'Karol')
        self.assertEqual(contact.email, 'karol@example.com')
        self.assertEqual(contact.role, 'Konsultant')
