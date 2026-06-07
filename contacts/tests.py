from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.urls import reverse

from .models import Company, Contact, SharedItem, UserContact


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
        self.other_user.save(update_fields=['profile_photo'])
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
            'status': 'lead',
            'last_contacted_at': '',
            'notes': '',
        })

        contact = Contact.objects.get(user=self.owner, email='ewa@acme.example.com')
        self.assertRedirects(response, reverse('contacts:view-contact', args=[contact.pk]))
        self.assertEqual(contact.company_record, company)
        self.assertEqual(contact.company, 'Acme')

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
