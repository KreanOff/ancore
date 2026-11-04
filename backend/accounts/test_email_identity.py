
from asgiref.sync import async_to_sync
from django.contrib.auth import SESSION_KEY, aauthenticate, authenticate, get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from workplaces.models import create_workplace_for_user
from workplaces.team_views import AddMemberForm
from .forms import UserRegistrationForm, UserProfileForm
from .views import _save_user_form


class EmailIdentityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username='email-owner', email='Anna@example.test')

    def registration(self, email='anna@example.test'):
        return UserRegistrationForm(data={
            'first_name': 'Anna', 'last_name': 'Nowak', 'email': email,
            'password1': 'registration-83-long!', 'password2': 'registration-83-long!',
        })

    def test_registration_rejects_case_duplicate_including_inactive_account(self):
        for active in (True, False):
            with self.subTest(active=active):
                get_user_model().objects.filter(pk=self.user.pk).update(is_active=active)
                form = self.registration('ANNA@EXAMPLE.TEST')
                self.assertFalse(form.is_valid())
                self.assertIn('email', form.errors)

    def test_profile_allows_own_email_case_but_rejects_another_account(self):
        data = {'first_name': 'Anna', 'last_name': 'Nowak', 'username': '@anna',
                'email': 'ANNA@example.test', 'presence_status': 'inactive'}
        form = UserProfileForm(data=data, instance=self.user)
        self.assertTrue(form.is_valid(), form.errors)
        other = get_user_model().objects.create_user(username='other-email', email='other@example.test')
        form = UserProfileForm(data=data, instance=other)
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)

    def test_database_rejects_case_duplicates_on_insert_and_update(self):
        User = get_user_model()
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.create_user(username='duplicate-email', email='anna@example.test')
        other = User.objects.create_user(username='other-email', email='other@example.test')
        with self.assertRaises(IntegrityError), transaction.atomic():
            User.objects.filter(pk=other.pk).update(email='ANNA@example.test')

    def test_duplicate_created_after_validation_becomes_form_error(self):
        form = self.registration('new@example.test')
        self.assertTrue(form.is_valid(), form.errors)
        get_user_model().objects.create_user(username='race-winner', email='NEW@example.test')
        self.assertFalse(_save_user_form(form))
        self.assertIn('email', form.errors)
        self.assertEqual(get_user_model().objects.filter(email__iexact='new@example.test').count(), 1)

    def test_manual_membership_uses_account_identity_instead_of_email(self):
        owner = get_user_model().objects.create_user(username='team-owner', email='team@example.test')
        workspace = create_workplace_for_user(owner, 'Email test')
        form = AddMemberForm(data={'user_id': str(self.user.pk), 'email': 'ANNA@example.test', 'role': 'member'}, workplace=workspace, actor=owner)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['user_id'], self.user)

    def test_authentication_and_login_accept_email_case_variants(self):
        password = 'email-authentication-83!'
        self.user.set_password(password)
        self.user.save(update_fields=['password'])
        for email in ('anna@example.test', 'ANNA@EXAMPLE.TEST'):
            with self.subTest(email=email):
                self.assertEqual(authenticate(username=email, password=password), self.user)
                self.assertEqual(async_to_sync(aauthenticate)(email=email, password=password), self.user)
                self.client.logout()
                response = self.client.post(reverse('login'), {'username': email, 'password': password})
                self.assertEqual(response.status_code, 302)
                self.assertEqual(self.client.session[SESSION_KEY], str(self.user.pk))

    def test_email_case_does_not_bypass_password_or_active_account_check(self):
        self.user.set_password('email-authentication-83!')
        self.user.save(update_fields=['password'])
        self.assertIsNone(authenticate(username='ANNA@EXAMPLE.TEST', password='wrong-password'))
        self.user.is_active = False
        self.user.save(update_fields=['is_active'])
        self.assertIsNone(authenticate(username='ANNA@EXAMPLE.TEST', password='email-authentication-83!'))

    def test_case_variant_works_after_logging_out_of_another_account(self):
        self.user.set_password('email-authentication-83!')
        self.user.save(update_fields=['password'])
        other = get_user_model().objects.create_user(username='signed-in', email='signed-in@example.test')
        self.client.force_login(other)
        self.client.post(reverse('logout'))
        response = self.client.post(reverse('login'), {'username': 'ANNA@EXAMPLE.TEST', 'password': 'email-authentication-83!'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session[SESSION_KEY], str(self.user.pk))

    def test_existing_model_backend_session_remains_authenticated(self):
        self.client.force_login(self.user, backend='django.contrib.auth.backends.ModelBackend')
        self.assertEqual(self.client.get(reverse('profile')).status_code, 200)
